from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^$', 'frontend.views.main.home', name='home'),
    url(r'^sources/create', 'frontend.views.sources.create',
        name='create_source'),
)
