from django.urls import path

from apps.guidance import views_admin, views_adviser, views_catalog, views_ratings, views_student

ADVISEE = 'advisory/<int:assignment_id>/students/<int:student_id>/'

urlpatterns = [
    path('programs/', views_catalog.ProgramCatalogView.as_view(), name='guidance-programs'),
    path('me/', views_student.GuidanceOverviewView.as_view(), name='guidance-me'),
    path('me/consent/', views_student.ConsentView.as_view(), name='guidance-consent'),
    path('me/consent/withdraw/', views_student.ConsentWithdrawView.as_view(), name='guidance-consent-withdraw'),
    path('me/assessment/', views_student.AssessmentView.as_view(), name='guidance-assessment'),
    path('me/assessment/start/', views_student.AssessmentStartView.as_view(), name='guidance-assessment-start'),
    path('me/assessment/answer/', views_student.AssessmentAnswerView.as_view(), name='guidance-assessment-answer'),
    path('me/assessment/complete/', views_student.AssessmentCompleteView.as_view(), name='guidance-assessment-complete'),
    path('me/programs/<slug:code>/', views_student.ProgramFitView.as_view(), name='guidance-program-fit'),
    path('me/compare/', views_student.CompareView.as_view(), name='guidance-compare'),
    path('advisory/<int:assignment_id>/', views_adviser.AdvisoryGuidanceView.as_view(), name='guidance-advisory'),
    path(ADVISEE, views_adviser.AdviseeView.as_view(), name='guidance-advisee'),
    path(f'{ADVISEE}notes/', views_adviser.AdviserNoteView.as_view(), name='guidance-advisee-note'),
    path(f'{ADVISEE}recommendation/', views_adviser.AdviserRecommendationView.as_view(), name='guidance-advisee-recommendation'),
    path(f'{ADVISEE}outcome/', views_adviser.OutcomeView.as_view(), name='guidance-advisee-outcome'),
    path('ratings/', views_ratings.RatingFormView.as_view(), name='guidance-ratings'),
    path('admin/catalog/', views_admin.CatalogView.as_view(), name='guidance-admin-catalog'),
    path('admin/families/', views_admin.FamilyCreateView.as_view(), name='guidance-admin-families'),
    path('admin/families/<slug:code>/', views_admin.FamilyDetailView.as_view(), name='guidance-admin-family'),
    path('admin/interest-map/', views_admin.InterestMapView.as_view(), name='guidance-admin-interest-map'),
    path('admin/programs/', views_admin.ProgramCreateView.as_view(), name='guidance-admin-programs'),
    path('admin/programs/import/', views_admin.CatalogImportView.as_view(), name='guidance-admin-import'),
    path('admin/programs/<slug:code>/', views_admin.ProgramDetailView.as_view(), name='guidance-admin-program'),
    path('admin/programs/<slug:code>/<slug:action>/', views_admin.ProgramActionView.as_view(), name='guidance-admin-program-action'),
    path('admin/instruments/', views_admin.InstrumentListView.as_view(), name='guidance-admin-instruments'),
    path('admin/instruments/<int:pk>/activate/', views_admin.InstrumentActivateView.as_view(), name='guidance-admin-instrument-activate'),
    path('admin/outcomes/', views_admin.OutcomeListView.as_view(), name='guidance-admin-outcomes'),
    path('admin/outcomes/<int:pk>/validate/', views_admin.OutcomeValidateView.as_view(), name='guidance-admin-outcome-validate'),
    path('admin/recommender/', views_admin.RecommenderStatusView.as_view(), name='guidance-admin-recommender'),
    path('admin/config/', views_admin.ConfigView.as_view(), name='guidance-admin-config'),
    path('admin/config/<int:pk>/activate/', views_admin.ConfigActivateView.as_view(), name='guidance-admin-config-activate'),
]
