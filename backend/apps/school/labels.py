def grade_number(grade_level):
    text = str(grade_level or '')
    if '11' in text:
        return '11'
    if '12' in text:
        return '12'
    return text.replace('Grade ', '').strip()


def section_label(section=None, *, grade_level='', program_code='', name=''):
    grade = grade_number(getattr(section, 'grade_level', None) or grade_level)
    program = ''
    if section is not None and getattr(section, 'program_id', None):
        program = section.program.code
    else:
        program = program_code or ''
    short = (getattr(section, 'name', None) if section is not None else name) or ''
    short = str(short).strip()
    head = ' - '.join(part for part in (grade, program) if part)
    if head and short:
        return f'{head} {short}'
    return head or short
