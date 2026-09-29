from django.urls import path

from .views_advisory import (
    AdvisoryGradesView,
    HideGradesView,
    PtpaAttendanceView,
    PtpaBulkView,
    ShowGradesView,
    ShowReadyView,
)
from .views_corrections import CorrectionListCreateView, CorrectionReviewView
from .views_history import GradeHistoryListView, GradeReportView
from .views_student import StudentGradesView
from .views_teacher import (
    TeacherClassGradesView,
    TeacherEncodeGradeView,
    TeacherGradeTimelineView,
    TeacherSubmitClassView,
)
from .views_workflow import (
    ApproveAllGradesView,
    ApproveGradesView,
    ApproveTeacherGradesView,
    GradeQueueView,
    ReturnGradesView,
)

urlpatterns = [
    path('me/', StudentGradesView.as_view(), name='student-grades'),
    path('class/', TeacherClassGradesView.as_view(), name='teacher-class-grades'),
    path('timeline/', TeacherGradeTimelineView.as_view(), name='teacher-grade-timeline'),
    path('encode/', TeacherEncodeGradeView.as_view(), name='teacher-encode-grade'),
    path('submit/', TeacherSubmitClassView.as_view(), name='teacher-submit-class'),
    path('advisory/', AdvisoryGradesView.as_view(), name='grade-advisory'),
    path('show/', ShowGradesView.as_view(), name='grade-show'),
    path('hide/', HideGradesView.as_view(), name='grade-hide'),
    path('ptpa/', PtpaAttendanceView.as_view(), name='grade-ptpa'),
    path('ptpa/bulk/', PtpaBulkView.as_view(), name='grade-ptpa-bulk'),
    path('show-ready/', ShowReadyView.as_view(), name='grade-show-ready'),
    path('queues/', GradeQueueView.as_view(), name='grade-queues'),
    path('approve/', ApproveGradesView.as_view(), name='grade-approve'),
    path('approve/teacher/', ApproveTeacherGradesView.as_view(), name='grade-approve-teacher'),
    path('approve/all/', ApproveAllGradesView.as_view(), name='grade-approve-all'),
    path('return/', ReturnGradesView.as_view(), name='grade-return'),
    path('history/', GradeHistoryListView.as_view(), name='grade-history'),
    path('report/', GradeReportView.as_view(), name='grade-report'),
    path('corrections/', CorrectionListCreateView.as_view(), name='grade-corrections'),
    path('corrections/<int:pk>/review/', CorrectionReviewView.as_view(), name='grade-correction-review'),
]
