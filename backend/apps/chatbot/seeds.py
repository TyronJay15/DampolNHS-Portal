from .models import FaqEntry
from .responses import SAFETY


FAQS = [
    (
        'registration',
        'register, sign up, create account, registration, enroll, mag enroll, mag register',
        'How do I register?',
        'Open Register, complete the student form, and submit. Your account stays pending until an administrator approves it.',
    ),
    (
        'registration',
        'registration requirements, what information, student form, kailangan sa registration, requirements',
        'What information do I need to register?',
        'Complete all required fields on the student registration form and check that your details are correct before submitting.',
    ),
    (
        'registration',
        'after registration, submitted application, next step, pagkatapos mag register, nag submit',
        'What happens after I submit my registration?',
        'Your student account waits for administrator review. Check the account status in the portal; contact the school through the Contact page if you need help.',
    ),
    (
        'registration',
        'wrong details, edit registration, correction, maling impormasyon, mali ang details',
        'How can I correct details in my registration?',
        'Contact the school through the Contact page and explain which registration details need correction.',
    ),
    (
        'registration',
        'registration status, application status, check status, status ng application, pending application',
        'How do I check my registration status?',
        'Sign in when your account is approved to view the portal. If you cannot access your account or need a status update, contact the school through the Contact page.',
    ),
    (
        'programs',
        'stem, abm, humss, ict, he, cluster, program, strand, available programs, anong strand',
        'What programs are offered?',
        'See the current program list and subjects on the Programs page. The available list depends on the school-year offerings.',
    ),
    (
        'programs',
        'subjects, subject list, subjects per program, mga subject, subjects ng strand',
        'Where can I see the subjects for each program?',
        'Open the Programs page and select a program to review its subjects.',
    ),
    (
        'programs',
        'choose program, select a strand, what should i take, anong program pipiliin, pagpili ng strand',
        'How do I choose a program?',
        'Review the current programs and their subjects on the Programs page. For enrollment advice, contact the school office through the Contact page.',
    ),
    (
        'programs',
        'program availability, offered this year, current strand, available ba, offered ngayon',
        'How do I know if a program is available this school year?',
        'Check the current program list on the Programs page and review school announcements for updates.',
    ),
    (
        'programs',
        'program details, strand information, curriculum, impormasyon sa program, detalye ng strand',
        'Where can I learn about a program?',
        'Visit the Programs page for the current program names and subject information.',
    ),
    (
        'login',
        'login, sign in, lrn, email, password, mag log in, hindi maka login',
        'How do I log in?',
        'Students sign in with LRN and password. Teachers and administrators sign in with school email and password.',
    ),
    (
        'login',
        'forgot password, reset password, change forgotten password, nakalimutan password, paano mag reset',
        'How do I reset a forgotten password?',
        'Choose Forgot password on the sign-in page and follow the email verification-code steps to set a new password.',
    ),
    (
        'login',
        'reset code, verification code, otp, no email code, walang natanggap na code',
        'What should I do if I do not receive a password reset code?',
        'Check that you used the email address on your account and look in your spam folder. If the code still does not arrive, contact the school through the Contact page.',
    ),
    (
        'login',
        'cannot sign in, login failed, wrong password, hindi makapasok, ayaw mag login',
        'Why can I not sign in?',
        'Check that you are using the correct account type and credentials. Student accounts must be approved; follow any activation prompt shown by the portal.',
    ),
    (
        'login',
        'student login, lrn login, teacher login, admin login, anong username, paano mag sign in',
        'Which username should I use to sign in?',
        'Students use their LRN. Teachers and administrators use their school email address.',
    ),
    (
        'approval',
        'pending, approval, approved, rejected, waiting, bakit pending, account status',
        'Why is my account pending?',
        'New student accounts wait for administrator review. You cannot sign in until the account is approved.',
    ),
    (
        'approval',
        'pending review, waiting for admin, account approval, naghihintay ma approve, hindi pa approved',
        'Who approves a new student account?',
        'An administrator reviews new student registrations. Contact the school through the Contact page if you need a status update.',
    ),
    (
        'approval',
        'rejected registration, application rejected, declined, nareject, rejected ang account',
        'What should I do if my registration was rejected?',
        'Review any notice shown by the portal and contact the school through the Contact page for help with your registration.',
    ),
    (
        'approval',
        'approval time, how long approval, when approved, gaano katagal ma approve, kailan maa approve',
        'How long does account approval take?',
        'The portal does not publish a fixed review time. Check school announcements or contact the school through the Contact page for updates.',
    ),
    (
        'grades',
        'grades, report card, approved, released, scores, kailan grades, nasaan grades',
        'When can I see my grades?',
        'Students see grades after the Head Teacher approves them and the adviser shows the report card.',
    ),
    (
        'grades',
        'missing grades, blank subject, no score, walang grade, kulang ang grades',
        'Why is a subject missing from my report card?',
        'A subject may not appear until its grades are approved and the report card is shown. Contact your adviser if you think a grade is missing.',
    ),
    (
        'grades',
        'wrong grade, score correction, grade dispute, maling score, mali ang grade',
        'What should I do if a grade looks incorrect?',
        'Contact your subject teacher or adviser and follow the grade-correction process available in the portal.',
    ),
    (
        'grades',
        'locked report card, hidden grades, cannot view grades, nakalock grades, hindi makita report card',
        'Why is my report card locked or hidden?',
        'The adviser controls when a report card is shown. Contact your adviser to check its status.',
    ),
    (
        'grades',
        'who approves grades, head teacher approval, grade release, sino nag aapprove ng grades',
        'Who approves and shows my grades?',
        'The Head Teacher approves submitted grades, then the adviser can show the report card to the student.',
    ),
    (
        'contact',
        'contact, facebook, deped, phone, email, address, paano makipag contact, contact school',
        'How do I contact the school?',
        'Use the Contact page for the school office details and official links.',
    ),
    (
        'contact',
        'school address, location, directions, saan ang school, lokasyon ng paaralan',
        'Where can I find the school address?',
        'Open the Contact page for the school address and official contact information.',
    ),
    (
        'contact',
        'school facebook, official facebook, social media, facebook page, opisyal na facebook',
        'Where can I find the official school Facebook page?',
        'Open the Contact page and use the official school links listed there.',
    ),
    (
        'contact',
        'office hours, school office schedule, open hours, oras ng opisina, anong oras bukas',
        'Where can I check the school office hours?',
        'Check the Contact page for the latest school office information.',
    ),
    (
        'events',
        'event, events, calendar, activity, upcoming, school event, mga event, aktibidad',
        'Where do I see upcoming events?',
        'Upcoming events appear on the dashboards after you sign in. Public news stays on the Announcements page.',
    ),
    (
        'events',
        'announcement, school news, notices, balita, announcement ng school',
        'Where can I read school announcements?',
        'Open the Announcements page for public school news and notices.',
    ),
    (
        'events',
        'event date, event time, schedule of activities, kailan ang event, oras ng activity',
        'Where can I check an event date or schedule?',
        'Check the event details on your dashboard or review the latest school announcements.',
    ),
    (
        'events',
        'cancelled event, postponed activity, event update, cancelled ba, na postpone',
        'How do I know if an event schedule changed?',
        'Review the latest school announcements and dashboard event details for schedule updates.',
    ),
    # A live topic: the chatbot answers it from the database (apps.chatbot.live_data), never from this text.
    # The row exists so the classifier learns the topic; its answer only describes the statistic.
    (
        'enrollment_stats',
        'how many students, number of students, total students, enrolled students, student population, '
        'ilan ang estudyante, ilan ang enrolled, ilang estudyante, kasalukuyang enrolled',
        'How many students are currently enrolled?',
        'The current enrollment total is calculated from approved registrations for the active school year.',
    ),
    (
        'approval',
        'enrollment status, enrollment approved, check enrollment, status ng enrollment, approved na ba, '
        'approved na ang enrollment',
        'How do I know if my enrollment is approved?',
        'Sign in with your LRN and password. While your registration is still pending, the sign-in page says your '
        'account is waiting for administrator approval. The school also emails you when your registration is '
        'approved or not approved.',
    ),
    (
        'grades',
        'where are my grades, view grades, grades menu, saan ang grades, makita ang grades, report card online',
        'Where can I see my grades in the portal?',
        'Sign in to the student portal and open Grades in the menu. A grade appears there after the Head Teacher '
        'approves it and your adviser shows the report card.',
    ),
    # Answered whenever moderation recognizes a report of bullying, harassment, threats or abuse.
    (
        'safety',
        'bullying, bullied, harassment, report bullying, inaapi, binubully, threat, abuse, guidance office',
        'How do I report bullying or harassment?',
        SAFETY,
    ),
]


def seed_faqs():
    created = 0
    for sort_order, (topic, keywords, question, answer) in enumerate(FAQS, start=1):
        _entry, was_created = FaqEntry.objects.get_or_create(
            question=question,
            defaults={
                'topic': topic,
                'keywords': keywords,
                'answer': answer,
                'sort_order': sort_order,
            },
        )
        created += int(was_created)
    return created