"""Shared event families for audit logs and notifications."""

ACCOUNTS = 'accounts'
SCHOOL = 'school'
ASSIGNMENTS = 'assignments'
PLACEMENT = 'placement'
GRADES = 'grades'
ANNOUNCEMENTS = 'announcements'

FAMILIES = (
    ACCOUNTS,
    SCHOOL,
    ASSIGNMENTS,
    PLACEMENT,
    GRADES,
    ANNOUNCEMENTS,
)

ACTIONS = {
    'register': {'family': ACCOUNTS, 'label': 'Registration submitted'},
    'login': {'family': ACCOUNTS, 'label': 'Signed in'},
    'password_otp_requested': {'family': ACCOUNTS, 'label': 'Password code sent'},
    'password_change': {'family': ACCOUNTS, 'label': 'Password changed'},
    'account_approved': {'family': ACCOUNTS, 'label': 'Student approved'},
    'account_rejected': {'family': ACCOUNTS, 'label': 'Student rejected'},
    'account_archived': {'family': ACCOUNTS, 'label': 'Account archived'},
    'account_reactivated': {'family': ACCOUNTS, 'label': 'Account reactivated'},
    'account_removed': {'family': ACCOUNTS, 'label': 'Account removed'},
    'registration_restored_pending': {'family': ACCOUNTS, 'label': 'Registration reopened'},
    'student_profile_updated': {'family': ACCOUNTS, 'label': 'Student profile updated'},
    'staff_created': {'family': ACCOUNTS, 'label': 'Staff created'},
    'staff_activated': {'family': ACCOUNTS, 'label': 'Staff activated'},
    'staff_activation_resent': {'family': ACCOUNTS, 'label': 'Activation resent'},
    'school_year_created': {'family': SCHOOL, 'label': 'School year opened'},
    'school_year_archived': {'family': SCHOOL, 'label': 'School year archived'},
    'school_year_restored': {'family': SCHOOL, 'label': 'School year restored'},
    'school_year_deleted': {'family': SCHOOL, 'label': 'School year deleted'},
    'school_year_hard_deleted': {'family': SCHOOL, 'label': 'School year hard deleted'},
    'deadline_set': {'family': SCHOOL, 'label': 'Encode window set'},
    'section_created': {'family': SCHOOL, 'label': 'Section created'},
    'section_deleted': {'family': SCHOOL, 'label': 'Section deleted'},
    'section_hard_deleted': {'family': SCHOOL, 'label': 'Section hard deleted'},
    'section_archived': {'family': SCHOOL, 'label': 'Section archived'},
    'section_restored': {'family': SCHOOL, 'label': 'Section restored'},
    'section_activated': {'family': SCHOOL, 'label': 'Section activated'},
    'section_activated_incomplete': {'family': SCHOOL, 'label': 'Section activated (incomplete)'},
    'program_created': {'family': SCHOOL, 'label': 'Program created'},
    'program_updated': {'family': SCHOOL, 'label': 'Program updated'},
    'model_trained': {'family': SCHOOL, 'label': 'Model retrained'},
    'adviser_assigned': {'family': ASSIGNMENTS, 'label': 'Adviser assigned'},
    'subject_teacher_assigned': {'family': ASSIGNMENTS, 'label': 'Subject teacher assigned'},
    'assignment_ended': {'family': ASSIGNMENTS, 'label': 'Assignment ended'},
    'assignment_purged': {'family': ASSIGNMENTS, 'label': 'Assignment purged'},
    'student_placed': {'family': PLACEMENT, 'label': 'Student placed'},
    'student_transferred': {'family': PLACEMENT, 'label': 'Student transferred'},
    'grades_submitted': {'family': GRADES, 'label': 'Grades submitted'},
    'grades_approved': {'family': GRADES, 'label': 'Grades approved'},
    'grades_returned': {'family': GRADES, 'label': 'Grades returned'},
    'grades_shown': {'family': GRADES, 'label': 'Card shown'},
    'grades_hidden': {'family': GRADES, 'label': 'Card hidden'},
    'grades_shown_ready': {'family': GRADES, 'label': 'Ready cards shown'},
    'ptpa_marked': {'family': GRADES, 'label': 'PTPA marked'},
    'correction_requested': {'family': GRADES, 'label': 'Correction requested'},
    'correction_approved': {'family': GRADES, 'label': 'Correction approved'},
    'correction_rejected': {'family': GRADES, 'label': 'Correction rejected'},
    'cms_save': {'family': ANNOUNCEMENTS, 'label': 'Website saved'},
    'announcement_published': {'family': ANNOUNCEMENTS, 'label': 'Event published'},
}


def family_for_action(action):
    entry = ACTIONS.get(action)
    return entry['family'] if entry else ACCOUNTS


def label_for_action(action):
    entry = ACTIONS.get(action)
    if entry:
        return entry['label']
    return str(action or '').replace('_', ' ').title()


def infer_notification_category(title='', body=''):
    text = f'{title} {body}'.lower()
    if 'event' in text or 'upcoming' in text:
        return ANNOUNCEMENTS
    if any(word in text for word in ('grade', 'report card', 'correction', 'encode', 'ptpa', 're-show')):
        return GRADES
    if any(word in text for word in ('assigned', 'adviser', 'subject assignment', 'classes are ready')):
        return ASSIGNMENTS
    if any(word in text for word in ('placed', 'transferred', 'roster')):
        return PLACEMENT
    if any(word in text for word in ('section', 'school year', 'encode window', 'activate')):
        return SCHOOL
    if any(word in text for word in ('account', 'registration', 'password', 'archived', 'restored', 'approved')):
        return ACCOUNTS
    return ACCOUNTS
