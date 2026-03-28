from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField, AdminPasswordChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin, StackedInline

from accounts.models import User, ClientProfile, CollectorProfile, AdminProfile, InvitationCode


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "full_name", "phone_number_1")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=
        "Raw passwords are not stored, so there is no way to see this "
        "user's password, but you can change the password using "
        "<a href=\"{}\">this form</a>."
        ,
    )

    class Meta:
        model = User
        fields = (
            'email', 'password', 'full_name', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].help_text = self.fields[
            'password'].help_text.format('../password/')
        f = self.fields.get('user_permissions')
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class ClientProfileAdmin(StackedInline):
    model = ClientProfile
    can_delete = False
    verbose_name_plural = 'Client Profile'
    fields = ('alias', 'identity_document', 'address_line_1', 'neighborhood', 'city', 'route', 'is_active', 'visit_order')
    readonly_fields = ('route',)


class CollectorProfileAdmin(StackedInline):
    model = CollectorProfile
    can_delete = False
    verbose_name_plural = 'Collector Profile'
    fields = ('admin', 'route', 'is_active')
    readonly_fields = ('route',)


class AdminProfileAdmin(StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = 'Admin Profile'


class UserAdmin(ModelAdmin, BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('email', 'full_name', 'phone_number_1', 'is_active')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone_number_1', 'phone_number_2', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number_1', 'role', 'password1', 'password2'),
        }),
    )

    ordering = ('id',)
    inlines = (ClientProfileAdmin, CollectorProfileAdmin, AdminProfileAdmin)

    readonly_fields = ('date_joined',)

admin.site.register(User, UserAdmin)
admin.site.unregister(Group)

@admin.register(InvitationCode)
class InvitationCodeAdmin(ModelAdmin):
    list_display = ('code', 'is_active', 'used_by', 'created_at')
    readonly_fields = ('used_at',)
