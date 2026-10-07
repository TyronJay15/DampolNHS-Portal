"""Interest-assessment seeds.

Version 1 is the O*NET Mini Interest Profiler, stored verbatim under CC BY-ND 4.0 (no local wording
changes). Version 2 is the Dampol SHS Interest Profiler: the same 30 Mini-IP activities rewritten as
personal, SHS-age "Would you enjoy…?" questions under the free O*NET Career Exploration Tools
Developer License, which allows modified items with the attribution below.

The school-facing instrument is version 2. A later migration opens it so students are not left on the
adult Mini-IP wording.
"""

from django.utils import timezone

CODE = 'onet-mini-ip'
LICENSE_URL = 'https://www.onetcenter.org/license_tools.html'
SOURCE_URL = 'https://www.onetcenter.org/dl_files/Mini-IP.pdf'
SOURCE = (
    'Rounds, J., Wee Jian Ming, C., Cao, M., Song, C., & Lewis, P. (2016). Development of an O*NET Mini Interest '
    'Profiler (Mini-IP) for mobile devices: Psychometric characteristics. National Center for O*NET Development.'
)

VERSION = 1
NAME = 'O*NET® Mini Interest Profiler'
ATTRIBUTION = (
    'This page includes information from the O*NET Career Exploration Tools by the U.S. Department of Labor, '
    'Employment and Training Administration (USDOL/ETA). Used under the CC BY-ND 4.0 license. '
    'O*NET is a trademark of USDOL/ETA.'
)

# (position, RIASEC type, item text)
ITEMS = (
    (1, 'R', 'Build kitchen cabinets'),
    (2, 'I', 'Develop a new medicine'),
    (3, 'A', 'Write books or plays'),
    (4, 'S', 'Help people with personal or emotional problems'),
    (5, 'E', 'Manage a department within a large company'),
    (6, 'C', 'Install software across computers on a large network'),
    (7, 'R', 'Repair household appliances'),
    (8, 'I', 'Study ways to reduce water pollution'),
    (9, 'A', 'Compose or arrange music'),
    (10, 'S', 'Give career guidance to people'),
    (11, 'E', 'Start your own business'),
    (12, 'C', 'Operate a calculator'),
    (13, 'R', 'Assemble electronic parts'),
    (14, 'I', 'Conduct chemical experiments'),
    (15, 'A', 'Create special effects for movies'),
    (16, 'S', 'Perform rehabilitation therapy'),
    (17, 'E', 'Negotiate business contracts'),
    (18, 'C', 'Keep shipping and receiving records'),
    (19, 'R', 'Drive a truck to deliver packages to offices and homes'),
    (20, 'I', 'Examine blood samples using a microscope'),
    (21, 'A', 'Paint sets for plays'),
    (22, 'S', 'Do volunteer work at a non-profit organization'),
    (23, 'E', 'Market a new line of clothing'),
    (24, 'C', 'Inventory supplies using a hand-held computer'),
    (25, 'R', 'Test the quality of parts before shipment'),
    (26, 'I', 'Develop a way to better predict the weather'),
    (27, 'A', 'Write scripts for movies or television shows'),
    (28, 'S', 'Teach a high-school class'),
    (29, 'E', 'Sell merchandise at a department store'),
    (30, 'C', 'Stamp, sort, and distribute mail for an organization'),
)

DAMPOL_VERSION = 2
DAMPOL_NAME = 'Dampol SHS Interest Profiler'
DAMPOL_ATTRIBUTION = (
    'This product was created using information from O*NET products. Those products were created by the '
    'National Center for O*NET Development for the U.S. Department of Labor, Employment and Training '
    'Administration (USDOL/ETA). O*NET® is a trademark of USDOL/ETA. This product has not been reviewed '
    'or endorsed by USDOL/ETA.'
)
DAMPOL_CHANGE_NOTE = (
    'Personal SHS-age rewrite of the Mini-IP activity under the O*NET Career Exploration Tools Developer License.'
)
ACTIVE_MARK = 'active'

# Same Holland type and position as ITEMS. original_text stays the Mini-IP stem.
DAMPOL_ITEMS = (
    (1, 'R', 'Would you enjoy building a wooden shelf or small furniture for your room?'),
    (2, 'I', 'Would you enjoy figuring out a new way to treat an illness?'),
    (3, 'A', 'Would you enjoy writing stories, books, or plays?'),
    (4, 'S', 'Would you enjoy helping a classmate who is going through a hard time?'),
    (5, 'E', 'Would you enjoy leading a team or club in a big school project?'),
    (6, 'C', 'Would you enjoy setting up apps or accounts on several computers?'),
    (7, 'R', 'Would you enjoy repairing a broken appliance or gadget at home?'),
    (8, 'I', 'Would you enjoy studying how to keep rivers and seas cleaner?'),
    (9, 'A', 'Would you enjoy composing or arranging music?'),
    (10, 'S', 'Would you enjoy giving advice about school or career choices?'),
    (11, 'E', 'Would you enjoy starting a small business of your own?'),
    (12, 'C', 'Would you enjoy keeping track of numbers, lists, and records?'),
    (13, 'R', 'Would you enjoy assembling electronic kits or computer parts?'),
    (14, 'I', 'Would you enjoy doing chemistry experiments in a school lab?'),
    (15, 'A', 'Would you enjoy creating special effects for videos or films?'),
    (16, 'S', 'Would you enjoy helping someone recover after an injury or illness?'),
    (17, 'E', 'Would you enjoy making a deal or agreeing on a group project plan?'),
    (18, 'C', 'Would you enjoy keeping a log of items received and sent out?'),
    (19, 'R', 'Would you enjoy helping deliver packages around your barangay?'),
    (20, 'I', 'Would you enjoy looking at cells or samples under a microscope?'),
    (21, 'A', 'Would you enjoy painting sets for a school play?'),
    (22, 'S', 'Would you enjoy volunteering at a community, church, or barangay project?'),
    (23, 'E', 'Would you enjoy promoting a new product or school event?'),
    (24, 'C', 'Would you enjoy checking supplies with a scanner or phone app?'),
    (25, 'R', 'Would you enjoy checking whether products were made well before they are sold?'),
    (26, 'I', 'Would you enjoy finding a better way to forecast the weather?'),
    (27, 'A', 'Would you enjoy writing scripts for short films or YouTube videos?'),
    (28, 'S', 'Would you enjoy teaching a class of younger students?'),
    (29, 'E', 'Would you enjoy selling items at a school fair or store?'),
    (30, 'C', 'Would you enjoy sorting, labeling, and filing papers for a club or office?'),
)


def _seed(get_model, *, version, name, attribution, items, rewrite=False):
    instrument_model = get_model('guidance', 'InterestInstrument')
    question_model = get_model('guidance', 'InterestQuestion')
    originals = {position: text for position, _letter, text in ITEMS}
    instrument, created = instrument_model.objects.get_or_create(
        code=CODE,
        version=version,
        defaults={
            'name': name,
            'source': SOURCE,
            'source_url': SOURCE_URL,
            'license_url': LICENSE_URL,
            'attribution': attribution,
        },
    )
    if not created:
        fields = []
        if instrument.name != name:
            instrument.name = name
            fields.append('name')
        if instrument.attribution != attribution:
            instrument.attribution = attribution
            fields.append('attribution')
        if fields:
            instrument.save(update_fields=fields)
    if created:
        question_model.objects.bulk_create(
            [
                question_model(
                    instrument=instrument,
                    position=position,
                    riasec=letter,
                    text=text,
                    original_text=originals[position],
                    change_note=DAMPOL_CHANGE_NOTE if rewrite else '',
                )
                for position, letter, text in items
            ]
        )
        return instrument
    if rewrite:
        _sync_questions(instrument, question_model, items, originals)
    return instrument


def _sync_questions(instrument, question_model, items, originals):
    existing = {row.position: row for row in question_model.objects.filter(instrument=instrument)}
    to_create = []
    for position, letter, text in items:
        row = existing.get(position)
        if row is None:
            to_create.append(
                question_model(
                    instrument=instrument,
                    position=position,
                    riasec=letter,
                    text=text,
                    original_text=originals[position],
                    change_note=DAMPOL_CHANGE_NOTE,
                )
            )
            continue
        fields = []
        if row.text != text:
            row.text = text
            fields.append('text')
        if row.riasec != letter:
            row.riasec = letter
            fields.append('riasec')
        if row.original_text != originals[position]:
            row.original_text = originals[position]
            fields.append('original_text')
        if row.change_note != DAMPOL_CHANGE_NOTE:
            row.change_note = DAMPOL_CHANGE_NOTE
            fields.append('change_note')
        if fields:
            row.save(update_fields=fields)
    if to_create:
        question_model.objects.bulk_create(to_create)


def seed_instrument(get_model):
    return _seed(get_model, version=VERSION, name=NAME, attribution=ATTRIBUTION, items=ITEMS)


def seed_dampol_instrument(get_model):
    return _seed(
        get_model,
        version=DAMPOL_VERSION,
        name=DAMPOL_NAME,
        attribution=DAMPOL_ATTRIBUTION,
        items=DAMPOL_ITEMS,
        rewrite=True,
    )


def open_dampol_instrument(get_model):
    """Seed or refresh version 2 and make it the only open instrument. Used by migrations."""
    instrument = seed_dampol_instrument(get_model)
    instrument_model = get_model('guidance', 'InterestInstrument')
    now = timezone.now()
    instrument_model.objects.filter(active_marker=ACTIVE_MARK).exclude(pk=instrument.pk).update(active_marker=None)
    fields = ['active_marker']
    instrument.active_marker = ACTIVE_MARK
    if not instrument.activated_at:
        instrument.activated_at = now
        fields.append('activated_at')
    if not instrument.license_confirmed_at:
        instrument.license_confirmed_at = now
        fields.append('license_confirmed_at')
    instrument.save(update_fields=fields)
    return instrument
