# -*- encoding: utf-8 -*-
from django.core import mail
from django.core.urlresolvers import reverse
from django.views.generic import CreateView, TemplateView, UpdateView
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from rest_framework.authtoken.models import Token

from accounts.forms import SignupForm, ProfileForm
from accounts.models import User, Organization


class SignupView(CreateView):

    form_class = SignupForm
    template_name = 'accounts/signup.html'
    success_url = '/accounts/signup_success/'

    def get_success_url(self):
        success_url = super(SignupView, self).get_success_url()
        if self.object.organization.is_provider:
            success_url += '?is_provider=True'
        return success_url

    def form_valid(self, form):
        """
        If the form is valid, save the associated model.
        """
        user = form.save(commit=False)
        confirmation_code = user.generate_confirmation_code()
        confirmation_path = reverse('accounts:confirm_email', kwargs={
            'confirmation_code': confirmation_code
        })
        confirmation_url = self.request.build_absolute_uri(confirmation_path)
        user.send_confirmation_email(confirmation_url)
        organization = form.cleaned_data['organization_list']
        if organization:
            user.organization = organization
        else:
            user.organization = Organization.objects.create()
            user.organization.update(form.cleaned_data)
        user.save()
        Token.objects.create(user=user)
        self.object = user
        return HttpResponseRedirect(self.get_success_url())


class EmailConfirmationView(TemplateView):

    template_name = 'accounts/email_confirmation.html'

    def activate_user(self, user):
        user.is_active = True
        user.save()

    def send_moderation_request_email(self, user):
        path = reverse('admin:accounts_user_change', args=(user.id, ))
        url = self.request.build_absolute_uri(path)

        tpl_name = 'accounts/email_admin_provider_validation.html'
        message = render_to_string(tpl_name, {'prov_validation_url': url})
        mail.send_mail(
            subject=_(u"Nouveau fournisseur de données"),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.ACCOUNTS_MODERATOR_EMAILS,
            fail_silently=False)

    def get(self, request, confirmation_code, *args, **kwargs):
        try:
            user = User.objects.get(confirmation_code=confirmation_code)
            if user.organization.is_provider:
                self.account_is_provider = True
                self.send_moderation_request_email(user)
            else:
                self.activate_user(user)
            self.success = True
        except User.DoesNotExist:
            self.success = False
        return super(EmailConfirmationView, self).get(request, *args, **kwargs)


class SignupSuccess(TemplateView):

    template_name = 'accounts/signup_success.html'


class ProfileView(UpdateView):

    template_name = 'accounts/profile.html'
    form_class = ProfileForm
    organization_fields = Organization._meta.get_all_field_names()
    organization_fields.remove('id')
    organization_fields.remove('user')

    def get_success_url(self):
        return reverse('accounts:profile')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProfileView, self).dispatch(*args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super(ProfileView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        organization = self.get_object().organization
        organization.update(form.cleaned_data)
        messages.success(self.request, _(u"Profil sauvegardé avec succès"))
        return super(ProfileView, self).form_valid(form)

    def get_initial(self):
        initial = super(ProfileView, self).get_initial()
        user = self.get_object()
        organization = user.organization
        for name in self.organization_fields:
            initial['organization_' + name] = getattr(organization, name)
        for contact_type in Organization.CONTACT_TYPES:
            for attr in ('name', 'email', 'phone_number'):
                if getattr(organization, contact_type):
                    contact = getattr(organization, contact_type)
                    field = 'organization_{}_{}'.format(contact_type, attr)
                    initial[field] = getattr(contact, attr)
        return initial
