"""The W guide's pages from Tinkers' own books (Mantle's book format), in every language the books are written in.

Each book becomes a small tree the player walks with links and the guide's Contents and Back: the guide's first page
lists the books; a book's page lists its sections; a section's page lists its pages; each page of the book is a page
of the guide, as short as the book's (a title, a few lines, its picture or items). Translations go to
`ae2guide/_<lang>/` (the kit reads the game's language there first), titles to the index's `titles_<lang>`.

Usage (from make_content.py): tconstruct_guide.write(files, jar)
"""

import json
import re
import zipfile

ID = "tconstruct"
# The order a player meets them in: the first two are the books Tinkers gives, the rest come later.
BOOKS = ["materials_and_you", "puny_smelting", "mighty_smelting", "tinkers_gadgetry", "fantastic_foundry", "encyclopedia"]
PREFIX = f"assets/{ID}/book/"


def read_json(z, path):
    try:
        return json.loads(z.read(path).decode("utf-8-sig"))
    except (KeyError, ValueError):
        return None


def read_lang(z, path):
    """A book's language.lang: key=value lines."""
    out = {}
    try:
        text = z.read(path).decode("utf-8-sig")
    except KeyError:
        return out
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


JAR = []   # the jar being read (structure pages read its structure files)
PICTURES = set()   # the book pictures the pages show ("book/images/...")


def item_of(v):
    """A book's item reference ({"item": id}, an id, or a Forge NBT ingredient) as an id."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        inner = v.get("item")
        if isinstance(inner, dict):
            return item_of(inner)
        if isinstance(inner, str):
            return inner
        if "id" in v:
            return v["id"]
    if isinstance(v, list) and v:
        return item_of(v[0])
    return None


def text_of(segments):
    """Mantle's text segments as short Markdown: bold kept, paragraphs as paragraphs, colours and actions dropped."""
    if isinstance(segments, str):
        return segments
    out = ""
    for s in segments or []:
        if isinstance(s, str):
            out += s
            continue
        t = s.get("text", "")
        t = re.sub(r"\$\([^)]*\)", "", t)  # Mantle's inline macros
        if s.get("bold") and t.strip():
            t = f"**{t.strip()}** " if t.endswith(" ") else f"**{t.strip()}**"
        if s.get("italic") and t.strip():
            t = f"*{t.strip()}*"
        # Mantle's TextData.toHTML: `paragraph` starts a new paragraph before the text, `linebreak` breaks after it.
        if s.get("paragraph") and out:
            out = out.rstrip(" ") + ("" if out.endswith("\n\n") else "\n\n" if not out.endswith("\n") else "\n")
        out += t
        if s.get("linebreak"):
            out += "\n"
    # The books write lists as "• item" lines: the guide's own list items (its font has no "•", drawn as "�").
    out = re.sub(r"(?m)^[ \t]*•[ \t]*", "- ", out).replace("•", "-")
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def page_body(page, files):
    """A book page as the guide's Markdown body, and the items it is about."""
    items = []
    lines = []
    image = page.get("image")
    if isinstance(image, dict) and image.get("file"):
        ns, path = image["file"].split(":", 1) if ":" in image["file"] else (ID, image["file"])
        rel = path.replace("book/images/", "book/")
        PICTURES.add(path)
        lines.append(f"![]({ID}:{rel})")   # namespaced: the page's own folder is not where pictures are
        lines.append("")
    data = page.get("data")
    if isinstance(data, str) and data.endswith(".nbt"):
        # A structure page (Mantle's multiblock): the book's structure as a 3D scene, formed.
        lines.append(structure_scene(files, data))
        lines.append("")
    for key in ("item", "block"):
        it = item_of(page.get(key))
        if it:
            items.append(it)
            lines.append(f'<ItemImage id="{it}" scale="2" />')
            lines.append("")
    tool = page.get("tool")
    if isinstance(tool, str):
        items.append(tool)
        lines.append(f'<ItemImage id="{tool}" scale="2" />')
        lines.append("")
    text = text_of(page.get("text"))
    if text:
        lines.append(text)
    effects = page.get("effects")
    if isinstance(effects, list) and effects:
        lines.append("")
        lines.extend(f"- {e}" for e in effects if isinstance(e, str))
    props = page.get("properties")
    if isinstance(props, list) and props:
        lines.append("")
        lines.extend(f"- {p}" for p in props if isinstance(p, str))
    recipe = page.get("recipe")
    if isinstance(recipe, str):
        lines.append("")
        lines.append(f'<Recipe id="{recipe}" />')
    return "\n".join(lines).strip() + "\n", items


def front(title, items):
    head = f"---\nnavigation:\n  title: {title}\nitem_ids:"
    head += "".join(f"\n- {i}" for i in items) if items else " []"
    return head + "\n---\n\n"


def write(files, jar):
    z = zipfile.ZipFile(jar)
    names = z.namelist()
    JAR[:] = [z]
    # The books' pictures, where the kit draws a page's pictures from (the GUI atlas: textures/gui/guide/).
    langs = sorted({n[len(PREFIX):].split("/")[1] for n in names
                    if n.startswith(PREFIX) and n.count("/") >= 5 and re.fullmatch(r"[a-z]{2,3}_[a-z]{2}", n[len(PREFIX):].split("/")[1])})
    general = {}
    for lang in langs:
        try:
            general[lang] = json.loads(z.read(f"assets/{ID}/lang/{lang}.json").decode("utf-8-sig"))
        except KeyError:
            general[lang] = {}
    pages = {}            # name -> English text with front matter
    translated = {}       # lang -> {name: body}
    titles = {}           # lang -> {name: title}
    order = []
    parents = {}

    def add(name, title_by_lang, body_by_lang, items, parent):
        order.append(name)
        if parent:
            parents[name] = parent
        en_title = title_by_lang.get("en_us") or name
        pages[name] = front(en_title, items) + f"# {en_title}\n\n" + body_by_lang.get("en_us", "")
        for lang in langs:
            if lang == "en_us":
                continue
            t = title_by_lang.get(lang)
            if t:
                titles.setdefault(lang, {})[name] = t
            b = body_by_lang.get(lang)
            if b:
                translated.setdefault(lang, {})[name] = f"# {t or en_title}\n\n{b}"

    book_titles = {lang: {} for lang in langs}
    for book in BOOKS:
        for lang in langs:
            book_titles[lang][book] = general[lang].get(f"item.{ID}.{book}") or general.get("en_us", {}).get(f"item.{ID}.{book}") or book.replace("_", " ").title()

    # The guide's first page: the books.
    root_body = {lang: "\n".join(f"- [{book_titles[lang][b]}]({b}/index.md)" for b in BOOKS) + "\n" for lang in langs}
    add("index.md", {lang: general[lang].get(f"itemGroup.{ID}.general", "Tinkers' Construct") for lang in langs} | {"en_us": "Tinkers' Construct"},
        root_body, [], None)
    for book in BOOKS:
        index = read_json(z, f"{PREFIX}{book}/index.json") or []
        book_lang = {lang: read_lang(z, f"{PREFIX}{book}/{lang}/language.lang") for lang in langs}
        sections = []
        for sec in index:
            if not isinstance(sec, dict) or sec.get("data") in (None, "no-load"):
                continue
            listing = read_json(z, f"{PREFIX}{book}/{sec['data']}")
            if not isinstance(listing, list):
                continue
            sections.append((sec, listing))
        book_page = f"{book}/index.md"
        body = {}
        for lang in langs:
            lines = []
            for sec, _ in sections:
                name = book_lang[lang].get(sec["name"]) or book_lang["en_us"].get(sec["name"]) or sec["name"]
                lines.append(f"- [{name}]({sec['name']}/index.md)")
            body[lang] = "\n".join(lines) + "\n"
        icon = item_of(index[0].get("icon")) if index and isinstance(index[0], dict) else None
        add(book_page, {lang: book_titles[lang][book] for lang in langs}, body, [f"{ID}:{book}"], "index.md")
        for sec, listing in sections:
            sec_page = f"{book}/{sec['name']}/index.md"
            sec_items = [i for i in [item_of(sec.get("icon"))] if i]
            entries = []
            for entry in listing:
                if not isinstance(entry, dict) or not entry.get("data"):
                    continue
                # An entry without a name (a generated page): its data file's name.
                entry = dict(entry, name=entry.get("name") or entry["data"].rsplit("/", 1)[-1].removesuffix(".json"))
                entries.append(entry)
            # The section's page: its pages, one line each (their titles, else the entry's name).
            leaf_titles = {lang: {} for lang in langs}
            leaf_bodies = {}
            leaf_items = {}
            for entry in entries:
                for lang in langs:
                    page = read_json(z, f"{PREFIX}{book}/{lang}/{entry['data']}")
                    if page is None:
                        continue
                    if not isinstance(page, dict):
                        continue
                    body_text, items = page_body(page, files)
                    leaf_bodies.setdefault(entry["name"], {})[lang] = body_text
                    leaf_titles[lang][entry["name"]] = page.get("title") or book_lang[lang].get(entry["name"]) or entry["name"].replace("_", " ").title()
                    if lang == "en_us":
                        leaf_items[entry["name"]] = [i for i in items if ":" in i]
            # Pages of one title in a row (a topic over several book pages) are one guide page.
            merged = []
            for e in entries:
                if e["name"] not in leaf_bodies:
                    continue
                if merged and leaf_titles["en_us"].get(e["name"]) == leaf_titles["en_us"].get(merged[-1]["name"]):
                    head = merged[-1]["name"]
                    for lang, body_text in leaf_bodies[e["name"]].items():
                        old = leaf_bodies[head].get(lang)
                        leaf_bodies[head][lang] = (old + "\n" + body_text) if old else body_text
                    leaf_items[head] = leaf_items.get(head, []) + [i for i in leaf_items.get(e["name"], []) if i not in leaf_items.get(head, [])]
                    continue
                merged.append(e)
            entries = merged
            sec_body = {}
            for lang in langs:
                sec_body[lang] = "\n".join(
                    f"- [{leaf_titles[lang].get(e['name']) or leaf_titles['en_us'].get(e['name'], e['name'])}]({e['name']}.md)"
                    for e in entries if e["name"] in leaf_bodies) + "\n"
            sec_title = {lang: book_lang[lang].get(sec["name"]) or book_lang["en_us"].get(sec["name"]) or sec["name"] for lang in langs}
            add(sec_page, sec_title, sec_body, sec_items, book_page)
            for e in entries:
                if e["name"] not in leaf_bodies:
                    continue
                add(f"{book}/{sec['name']}/{e['name']}.md", {lang: leaf_titles[lang].get(e["name"]) for lang in langs},
                    leaf_bodies[e["name"]], leaf_items.get(e["name"], []), sec_page)
    # The pictures the pages show, at most 256 by 144 (Horizon's GUI atlas is nearly full: what won't pack is left
    # out, and the guide draws them at most 160 high anyway).
    from PIL import Image
    import io
    for path in sorted(PICTURES):
        try:
            im = Image.open(io.BytesIO(z.read(f"assets/{ID}/{path}"))).convert("RGBA")
        except KeyError:
            continue
        im.thumbnail((256, 144), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        files[f"assets/{ID}/textures/gui/guide/{path.replace('book/images/', 'book/')}"] = buf.getvalue()
    # Pages and the index, as guide_index.write lays them out, with these parents and the translated titles.
    import guide_index
    index = guide_index.write(files, ID, pages)
    index["parents"] = parents
    # A book's own item opens that book (other books' "further reading" pages name it too).
    # An item that is a section's icon opens the page about it, not the section's list.
    for name, text in pages.items():
        if not name.endswith("index.md"):
            for item in guide_index.front_matter(text)[1]:
                if index["items"].get(item, "index.md").endswith("index.md"):
                    index["items"][item] = name
    for book in BOOKS:
        index["items"][f"{ID}:{book}"] = f"{book}/index.md"
    # Every other Tinkers item opens the page about it (W is the guide's way in from any item): the books name only
    # some items on their pages, so the rest go by their family, then by a page named after them.
    link_items(files, index["items"], set(pages))
    index["positions"] = {name: str(at * 10) for at, name in enumerate(order)}
    for lang, by_page in titles.items():
        index[f"titles_{lang}"] = by_page
    files[f"data/{ID}/ae2guide/index.json"] = json.dumps(index, indent=1).encode()
    for lang, by_page in translated.items():
        for name, body in by_page.items():
            files[f"data/{ID}/ae2guide/_{lang}/{name}"] = body.encode()
    add_setup_scenes(files, pages)
    return len(pages), sorted(translated)


# (a regex on an item's path, the page it opens): Tinkers' families, the books' pages about them.
FAMILY_PAGES = [
    (r"^smeltery_controller$", "mighty_smelting/smeltery/controller.md"),
    (r"^foundry_controller$", "fantastic_foundry/foundry/controller.md"),
    (r"^seared_(melter|heater)$", "puny_smelting/melter/melter.md"),
    (r"alloyer$", "fantastic_foundry/alloyer/alloyer.md"),
    (r"faucet$", "puny_smelting/moving_fluids/faucets.md"),
    (r"channel$", "puny_smelting/moving_fluids/channels.md"),
    (r"fluid_cannon$", "puny_smelting/moving_fluids/fluid_cannon.md"),
    (r"^copper_can$", "puny_smelting/moving_fluids/copper_cans.md"),
    (r"gauge$", "puny_smelting/moving_fluids/gauge.md"),
    (r"casting_tank$", "puny_smelting/casting/casting_tank.md"),
    (r"_(table|basin)$", "puny_smelting/casting/casting.md"),
    (r"_sand_cast$", "puny_smelting/casting/sand_cast.md"),
    (r"_cast$", "puny_smelting/casting/gold_cast.md"),
    (r"^seared_(drain|duct|chute|ladder|glass|tinted_glass|soul_glass)$", "mighty_smelting/smeltery/{1}.md"),
    (r"^scorched_(drain|duct|chute|ladder|glass|tinted_glass|soul_glass)$", "fantastic_foundry/foundry/{1}.md"),
    (r"^seared_.*(tank|gauge|lantern)$", "mighty_smelting/smeltery/seared_tanks.md"),
    (r"^scorched_.*(tank|gauge|lantern)$", "fantastic_foundry/foundry/scorched_tanks.md"),
    (r"seared", "mighty_smelting/smeltery/seared_blocks.md"),
    (r"scorched", "fantastic_foundry/foundry/scorched_blocks.md"),
    (r"_cake$", "tinkers_gadgetry/gadgets/cake.md"),
    (r"piggy_?backpack", "tinkers_gadgetry/gadgets/piggybackpack.md"),
    (r"_item_frame$|fancy_frame", "tinkers_gadgetry/gadgets/fancy_frames.md"),
    (r"cobalt_ore", "tinkers_gadgetry/exploration/cobalt_ore.md"),
    (r"^(earth|sky|ichor|ender)_slime_crystal|budding_(earth|sky|ichor|ender)", "tinkers_gadgetry/exploration/{geode}"),
    (r"^(earth|sky|ender|blood|ichor)", "tinkers_gadgetry/exploration/{island}"),
    (r"(pick_head|small_axe_head|small_blade|adze_head|hammer_head|broad_axe_head|broad_blade|large_plate|tool_handle|"
     r"tough_handle|tool_binding|tough_binding|round_plate|bow_limb|bow_grip|bowstring|maille|shield_core|repair_kit|"
     r"_plating|_plating_dummy|arrow_shaft|fletching)$", "materials_and_you/intro/partbuilder.md"),
    (r"_head$|_wall_head$", "fantastic_foundry/blazing_blood/head.md"),
    # Tools and armour by the encyclopedia's groups.
    (r"^(pickaxe|mattock|pickadze|hand_axe|kama|dagger|sword|flint_and_brick)$", "encyclopedia/tools/group_small.md"),
    (r"^(sledge_hammer|vein_hammer|excavator|broad_axe|scythe|cleaver)$", "encyclopedia/tools/group_large.md"),
    (r"^(crossbow|longbow|fishing_rod|javelin|arrow|shuriken|throwing_axe|flint_shuriken|quartz_shuriken|crystalshot)$",
     "encyclopedia/tools/group_ranged.md"),
    (r"_staff$", "encyclopedia/tools/group_staff.md"),
    (r"^(melting_pan|war_pick|battlesign|swasher|minotaur_axe)$", "encyclopedia/tools/group_ancient.md"),
    (r"^(travelers|plate|slime|slimy)_(helmet|chestplate|leggings|boots|shield)$|^slime_wings$", "encyclopedia/armor/info.md"),
    # Materials: ores and shards where the books find them, alloys where the smeltery makes them.
    (r"cobalt", "tinkers_gadgetry/exploration/cobalt_ore.md"),
    (r"^steel_", "tinkers_gadgetry/exploration/steel_shard.md"),
    (r"^knightmetal_", "tinkers_gadgetry/exploration/knightmetal_shard.md"),
    (r"^(amethyst_bronze|cinderslime|hepatizon|manyullyn|rose_gold|pig_iron|queens_slime|slimesteel|soulsteel|"
     r"knightslime)_", "mighty_smelting/smeltery/alloying.md"),
    (r"^(blazing_blood|blazewood)", "fantastic_foundry/blazing_blood/index.md"),
    (r"_bucket$", "puny_smelting/moving_fluids/moving_fluids.md"),
    (r"^grout$", "mighty_smelting/smeltery/seared_blocks.md"),
    (r"^nether_grout$", "fantastic_foundry/foundry/scorched_blocks.md"),
    (r"^(clear|clear_tinted|.*_clear_stained|soul|obsidian)_glass|_pane$|^gold_bars$|_platform$|_nugget$|^fake_ingot$|_spaghetti$",
     "puny_smelting/casting/casting.md"),
    (r"_reinforcement$|^(silky_cloth|efln_ball|glow_ball|glow|ribcage|venombone|necronium_bone|blazing_bone|shell|laces|punji)$",
     "materials_and_you/modifiers/upgrades.md"),
    (r"^nahuatl", "materials_and_you/intro/partbuilder.md"),
    (r"^modifier_crystal$", "puny_smelting/worktable/index.md"),
    (r"^terracube", "tinkers_gadgetry/exploration/clay_island.md"),
    (r"(greenheart|slimy_mud_green|earth_slime_crystal_bud)", "tinkers_gadgetry/exploration/{earth}"),
    (r"(skyroot|slimy_mud_blue|sky_slime_crystal_bud)", "tinkers_gadgetry/exploration/{sky}"),
    (r"(bloodshroom|slimy_mud_magma)", "tinkers_gadgetry/exploration/blood_island.md"),
    (r"(enderbark|ender_slime_crystal_bud)", "tinkers_gadgetry/exploration/{ender}"),
    (r"^(bacon|cheese_|jeweled_apple|meat_soup|.*_bottle$)", "tinkers_gadgetry/gadgets/index.md"),
    (r"^(pattern|part_builder|tinker_station|tinkers_anvil|scorched_anvil|crafting_station|tinkers_chest|part_chest|"
     r"cast_chest|modifier_worktable)$", "materials_and_you/intro/tinkerstation.md"),
]


def link_items(files, items, page_names):
    """Gives each Tinkers item without a page of its own (the books link only some) the page of its family, else a
    page named after it or a word of its name, else the guide's front page."""
    import re
    all_items = sorted(name.rsplit("/", 1)[1][:-5] for name in files if name.startswith(f"assets/{ID}/items/")
                       and name.endswith(".json"))
    stems = {}
    for page in sorted(page_names):
        stems.setdefault(page.rsplit("/", 1)[-1][:-3], page)
    island = {"earth": "earthslime_island.md", "sky": "skyslime_island.md", "ender": "enderslime_island.md",
              "blood": "blood_island.md", "ichor": "blood_island.md"}
    geode = {"earth": "earthslime_geode.md", "sky": "skyslime_geode.md", "ichor": "ichor_geode.md",
             "ender": "enderslime_geode.md"}
    tools = set(t for t in re.findall(r'"([a-z_]+)"', (files.get(f"data/{ID}/tags/item/modifiable.json") or b"").decode()))
    for item in all_items:
        key = f"{ID}:{item}"
        # Kept: a page the books give the item, unless it is only a section's list (then its family's page, if any).
        listed = items.get(key)
        if listed and (not listed.endswith("index.md") or item in BOOKS):
            continue
        page = None
        for pattern, target in FAMILY_PAGES:
            m = re.search(pattern, item)
            if not m:
                continue
            kind = item.split("_", 1)[0].replace("budding", item.split("_")[1] if "_" in item else "")
            target = target.replace("{1}", next((g for g in m.groups() if g), ""))
            target = target.replace("{island}", island.get(kind, "")).replace("{geode}", geode.get(kind, ""))
            for slime in ("earth", "sky", "ender"):   # a wood is its island's, a crystal bud its geode's
                target = target.replace("{%s}" % slime, (geode if "crystal" in item else island)[slime])
            if target in page_names:
                page = target
                break
        if page is None and item in stems:
            page = stems[item]
        if page is None and (key in tools or item in tools):
            page = "encyclopedia/tools/index.md" if "encyclopedia/tools/index.md" in page_names else None
        if page is None:
            page = next((stems[w] for w in item.split("_") if len(w) > 3 and w in stems), None)
        items[key] = page or listed or "index.md"


def state_props(files, block, props):
    """`props` limited to the properties `block`'s block state file names (a scene's block draws only by those)."""
    raw = files.get(f"assets/{block.split(':')[0]}/blockstates/{block.split(':')[1]}.json")
    if not raw or not props:
        return {}
    text = raw.decode()
    return {k: v for k, v in props.items() if f"{k}=" in text or f'"{k}"' in text}


def structure_scene(files, data):
    """The scene of a book structure file ("tconstruct:book/structures/NAME.nbt"), its blocks as formed."""
    import guide_index
    import nbt
    ns, path = data.split(":", 1)
    name = path.rsplit("/", 1)[-1][:-4]
    blocks = []
    for x, y, z, block, props in nbt.structure_blocks(JAR[0].read(f"assets/{ns}/{path}")):
        if "in_structure" in props:
            props["in_structure"] = "true"
        blocks.append([x, y, z, block, state_props(files, block, props)])
    return guide_index.scene(files, ID, f"structure_{name}", blocks)


# 3D scenes of blocks working together, by page: [x, y, z, block, properties]. The guide first shows a scene from
# the north (-z), so fronts face north.
SETUP_SCENES = {
    # A melter on its heater, a faucet on its front pouring into a casting table.
    "puny_smelting/melter/melter.md": [
        [0, 0, 0, "tconstruct:seared_heater", {"facing": "north", "active": "false"}],
        [0, 1, 0, "tconstruct:seared_melter", {"facing": "north", "in_structure": "false"}],
        [0, 1, -1, "tconstruct:seared_faucet", {"facing": "north"}],
        [0, 0, -1, "tconstruct:seared_table", {"facing": "north"}]],
    # A tank's faucet over a table and one over a basin.
    "puny_smelting/casting/casting.md": [
        [0, 1, 0, "tconstruct:seared_fuel_tank", {}], [1, 1, 0, "tconstruct:seared_fuel_tank", {}],
        [0, 1, -1, "tconstruct:seared_faucet", {"facing": "north"}], [1, 1, -1, "tconstruct:seared_faucet", {"facing": "north"}],
        [0, 0, -1, "tconstruct:seared_table", {"facing": "north"}], [1, 0, -1, "tconstruct:seared_basin", {"facing": "north"}],
        [0, 0, 0, "tconstruct:seared_bricks", {}], [1, 0, 0, "tconstruct:seared_bricks", {}]],
    "puny_smelting/moving_fluids/faucets.md": [
        [0, 1, 0, "tconstruct:seared_fuel_tank", {}], [0, 1, -1, "tconstruct:seared_faucet", {"facing": "north"}],
        [0, 0, -1, "tconstruct:seared_table", {"facing": "north"}], [0, 0, 0, "tconstruct:seared_bricks", {}]],
    # The foundry's alloyer between two tanks of what it alloys.
    "fantastic_foundry/alloyer/alloyer.md": [
        [1, 0, 0, "tconstruct:scorched_alloyer", {"facing": "north", "active": "false"}],
        [0, 0, 0, "tconstruct:scorched_fuel_tank", {}], [2, 0, 0, "tconstruct:scorched_fuel_tank", {}],
        [1, 0, -1, "tconstruct:scorched_faucet", {"facing": "north"}], [1, -1, -1, "tconstruct:scorched_table", {"facing": "north"}],
        [1, -1, 0, "tconstruct:scorched_bricks", {}]],
}
# The other pages about blocks: each block with what it works with (tconstruct_scenes.py).
import tconstruct_scenes  # noqa: E402
SETUP_SCENES.update({k: v for k, v in tconstruct_scenes.SCENES.items() if k not in SETUP_SCENES})


# Pages about a part of the smeltery or foundry show the whole structure, the part in its place.
STRUCTURE_PAGES = {"structure_smeltery": ["mighty_smelting/smeltery/controller.md", "mighty_smelting/smeltery/seared_drain.md",
                                          "mighty_smelting/smeltery/seared_blocks.md", "mighty_smelting/smeltery/index.md",
                                          "mighty_smelting/smeltery/structurereq.md",
                                          # what the smeltery does: the smeltery doing it
                                          "mighty_smelting/smeltery/features.md", "mighty_smelting/smeltery/alloying.md",
                                          "mighty_smelting/entity_melting/entitymelting.md",
                                          "mighty_smelting/entity_melting/noteableentities.md"],
                   "structure_foundry": ["fantastic_foundry/foundry/controller.md", "fantastic_foundry/foundry/scorched_blocks.md",
                                         "fantastic_foundry/foundry/index.md", "fantastic_foundry/foundry/structurereq.md",
                                         # what the foundry does, and blazing blood (its fuel, made in it)
                                         "fantastic_foundry/foundry/features.md", "fantastic_foundry/foundry/byproducts.md",
                                         "fantastic_foundry/blazing_blood/foundry.md",
                                         "fantastic_foundry/blazing_blood/melting.md"]}


def add_setup_scenes(files, pages):
    """Puts each SETUP_SCENES scene, and the structures on their parts' pages, at the top of their pages (English
    and translated pages alike)."""
    import guide_index
    todo = []
    for page, blocks in SETUP_SCENES.items():
        # Tinkers blocks this port has, their properties as its block states name them; vanilla ones as given.
        ok = [[x, y, z, b, state_props(files, b, p) if b.startswith(ID + ":") else p] for x, y, z, b, p in blocks
              if not b.startswith(ID + ":") or f"assets/{ID}/blockstates/{b.split(':')[1]}.json" in files]
        if ok:
            todo.append((page, guide_index.scene(files, ID, "setup_" + page[:-3].replace("/", "_"), ok)))
    # Pages about items (tools, modifiers, materials, casts): the stations that make or change them.
    for page in pages:
        if page in SETUP_SCENES or page.endswith("index.md"):
            continue
        blocks = tconstruct_scenes.topic_scene(page)
        ok = [[x, y, z, b, state_props(files, b, p)] for x, y, z, b, p in blocks or []
              if f"assets/{ID}/blockstates/{b.split(':')[1]}.json" in files]
        if ok:
            todo.append((page, guide_index.scene(files, ID, "topic_" + page[:-3].replace("/", "_"), ok)))
    for name, on in STRUCTURE_PAGES.items():
        if f"data/{ID}/ae2guide/scenes/{name}.json" in files:
            tag = f'<GameScene zoom="3" interactive={{true}}>\n  <ImportStructure src="{ID}:scenes/{name}.snbt" />\n</GameScene>\n'
            todo += [(page, tag) for page in on]
    for page, tag in todo:
        for key in [k for k in files if k == f"data/{ID}/ae2guide/{page}"
                    or (k.startswith(f"data/{ID}/ae2guide/_") and k.split("/", 4)[-1] == page)]:
            if "<GameScene" in files[key].decode():
                continue
            body = files[key].decode()
            head, _, rest = body.partition("\n\n") if body.startswith("# ") else ("", "", body)
            files[key] = ((head + "\n\n" if head else "") + tag + "\n" + rest).encode()
