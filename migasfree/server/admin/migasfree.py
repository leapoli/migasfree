# -*- coding: utf-8 -*-

import inspect
import datetime

from six import iteritems

from import_export.admin import ExportActionModelAdmin

from django import forms
from django.apps import apps
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import BooleanField, IntegerField
from django.shortcuts import redirect, reverse, get_object_or_404
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.html import format_html
from django.template.loader import render_to_string


class MigasFields(object):
    @staticmethod
    def boolean(name="", description='', model=None):
        def getter(self, obj):
            style = 'fa-check boolean-yes'
            text = ugettext('Yes')
            if not getattr(obj, name):
                style = 'fa-times boolean-no'
                text = ugettext('No')

            html = '<span class="fas %s"></span><span class="sr-only">%s</span>'

            return format_html(html % (style, text))

        getter.admin_order_field = name

        getter.short_description = description \
            or _(model._meta.get_field(name).verbose_name)

        return getter

    @staticmethod
    def text(model=None, name="", description=''):
        def getter(self, obj):
            return format_html(getattr(obj, name).replace('{', '{{').replace('}', '}}'))

        getter.admin_order_field = name

        getter.short_description = description \
            or _(model._meta.get_field(name).verbose_name)

        return getter

    @staticmethod
    def link(name='', model=None, description=None, order=None):
        """
        Create a function that can be attached to a ModelAdmin to use
        as a list_display field
        """
        related_names = name.split('__')

        def getter(self, obj):
            for item in related_names:
                target = getattr(obj, item)
                if not (
                    isinstance(target, str)
                    or isinstance(target, datetime.datetime)
                    or target is None
                ):
                    obj = target
                else:
                    if target is None:
                        return ""

                if inspect.ismethod(obj):  # Is a method
                    obj = obj()

            return obj.link()

        getter.admin_order_field = order or name

        for related_name in related_names:
            if hasattr(model, "_meta"):
                try:
                    field = model
                    model = model._meta.get_field(related_name)
                    if model.get_internal_type() == "ForeignKey":
                        model = model.related_model
                        getter.short_description = description \
                            or _(model._meta.verbose_name.title())
                    else:
                        getter.short_description = description \
                            or _(field._meta.verbose_name.title())
                except:
                    pass

        return getter

    @staticmethod
    def objects_link(name='', description=None, model=None):
        """
        Create a function that can be attached to a ModelAdmin to use
        as a list_display field
        """
        related_names = name.split('__')

        def getter(self, obj):
            if not related_names[0]:
                return obj.link()

            for item in related_names:
                obj = getattr(obj, item)

            if inspect.ismethod(obj):  # Is a method
                obj = obj()

            if not hasattr(obj, 'all'):
                return obj.link()

            return format_html(
                render_to_string(
                    'includes/objects_link.html',
                    {
                        'objects': obj.all()
                    }
                )
            )

        for related_name in related_names:
            field = model
            if hasattr(model, "_meta"):
                related_name = related_name.replace("_set", "")
                if related_name in model._meta.fields_map:
                    model = model._meta.fields_map[related_name]
                elif inspect.ismethod(model):  # Is a method
                    getter.short_description = description \
                        or getattr(model, related_name).short_description
                    return getter
                else:

                    if inspect.ismethod(getattr(model, related_name)):
                        getter.short_description = description \
                            or getattr(model, related_name).short_description
                        return getter

                    else:
                        try:
                            model = getattr(model, related_name).field
                            getter.short_description = description \
                                or _(model.verbose_name.title())
                            return getter
                        except AttributeError:
                            return getter

                if model.get_internal_type() in [
                    "ForeignKey", "ManyToManyField"
                ]:
                    model = model.related_model
                    getter.short_description = description \
                        or _(model._meta.verbose_name_plural.title())
                else:
                    getter.short_description = description \
                        or _(field._meta.verbose_name_plural.title())

        return getter

    @staticmethod
    def timeline():
        def getter(self, obj):
            if obj.schedule:
                return format_html(
                    render_to_string(
                        'includes/deployment_timeline.html',
                        {
                            'timeline': obj.timeline()
                        }
                    )
                )
            else:
                return ""

        getter.short_description = _("time line")

        return getter


class MigasAdmin(ExportActionModelAdmin):
    list_display_links = None
    filter_description = ''
    list_per_page = 10

    def get_changelist(self, request, **kwargs):
        return MigasChangeList

    def get_form(self, request, obj=None, **kwargs):
        form = super(MigasAdmin, self).get_form(request, obj, **kwargs)
        for field in form.base_fields.keys():
            form.base_fields[field].widget.can_change_related = False
            form.base_fields[field].widget.can_add_related = False
            form.base_fields[field].widget.can_delete_related = False

        if self.model.__name__ in [
            'Store', 'Package', 'Deployment', 'Scope', 'InternalSource', 'ExternalSource'
        ]:
            class ModelFormMetaClass(forms.ModelForm):
                # adding request to ModelForm
                def __new__(cls, *args, **kwargs):
                    kwargs['request'] = request

                    return form(*args, **kwargs)

            return ModelFormMetaClass

        return form

    def get_queryset(self, request):
        if hasattr(self.model.objects, 'scope'):
            return self.model.objects.scope(request.user.userprofile)
        else:
            return super(MigasAdmin, self).get_queryset(request)

    @property
    def media(self):
        media = super(MigasAdmin, self).media
        media._js = list(filter(
            lambda i: not i.startswith('admin/js/vendor/jquery/jquery'),
            media._js
        ))

        return media


class MigasCheckAdmin(MigasAdmin):
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            url(
                r'^check/(?P<pk>\d+)/$',
                self.my_check,
                name='check_{}'.format(self.model._meta.model_name)
            ),
            url(
                r'^uncheck/(?P<pk>\d+)/$',
                self.my_uncheck,
                name='uncheck_{}'.format(self.model._meta.model_name)
            ),
        ]

        return my_urls + urls

    def my_check(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        obj.checked_ok()
        messages.success(request, _("%s checked!") % obj)

        return redirect(
            request.META.get(
                'HTTP_REFERER',
                'admin:{}_{}_changelist'.format(self.model._meta.app_label, self.model._meta.model_name)
            )
        )

    def my_uncheck(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        obj.uncheck_ok()
        messages.success(request, _("%s unchecked!") % obj)

        return redirect(
            request.META.get(
                'HTTP_REFERER',
                'admin:{}_{}_changelist'.format(self.model._meta.app_label, self.model._meta.model_name)
            )
        )

    def check_action(self, obj):
        style = 'btn-danger'
        icon = 'fa-times boolean-no'
        action = _('check')
        url_ = 'check_{}'.format(self.model._meta.model_name)
        if obj.checked:
            style = 'btn-success'
            icon = 'fa-check boolean-yes'
            action = _('uncheck')
            url_ = 'uncheck_{}'.format(self.model._meta.model_name)

        return format_html(
            '<a class="btn btn-default {} changelist-action" href="{}" title="{}">'
            '<span class="fas {}"></span><span class="sr-only">{}</span></a>'.format(
                style,
                reverse('admin:{}'.format(url_), kwargs={'pk': obj.id}),
                action,
                icon,
                action
            )
        )

    check_action.short_description = _('checked')
    check_action.admin_order_field = 'checked'


class MigasTabularInline(admin.TabularInline):
    @property
    def media(self):
        media = super(MigasTabularInline, self).media
        media._js = list(filter(lambda i: not i.startswith('admin/js/vendor/jquery/jquery'), media._js))

        return media


class MigasChangeList(ChangeList):
    def __init__(self, *args, **kwargs):
        super(MigasChangeList, self).__init__(*args, **kwargs)
        self.filter_description = []
        params = dict(self.params)
        remove = []

        for x in self.filter_specs:
            if hasattr(x, 'lookup_choices') \
                    and hasattr(x, 'used_parameters') and x.used_parameters:
                if hasattr(x, 'lookup_val') and not x.lookup_val:
                    element = ''
                    for key, value in iteritems(x.used_parameters):
                        lookup_type = key.split('__')[1]
                        if lookup_type == 'isnull':
                            element += ugettext('empty') if value else ugettext('not empty')
                        else:
                            element += '{}={}'.format(lookup_type, value)
                        params.pop(key, None)
                elif isinstance(x.lookup_choices[0][0], int):
                    element = dict(
                        x.lookup_choices
                    ).get(int(list(x.used_parameters.values())[0]), '')
                else:
                    element = dict(
                        x.lookup_choices
                    ).get(list(x.used_parameters.values())[0], '')

                self.append(x.title, element, list(x.used_parameters.keys())[0])
                for element in x.used_parameters:
                    params.pop(element, None)
            elif hasattr(x, 'lookup_choices') and hasattr(x, 'lookup_val') \
                    and x.lookup_val:
                value = dict(x.lookup_choices)[x.lookup_val]
                if isinstance(x.lookup_choices[0][0], int):
                    value = dict(x.lookup_choices)[int(x.lookup_val)]
                self.append(x.lookup_title, value, x.lookup_kwarg)
                params.pop(x.lookup_kwarg, None)
            elif hasattr(x, 'links'):
                for l in x.links:
                    if l[1] and hasattr(x, 'used_parameters') and l[1] == x.used_parameters:
                        self.append(
                            x.title,
                            l[0],
                            x.lookup_kwarg_since,
                            x.lookup_kwarg_until
                        )
                        remove.extend(l[1])
            elif hasattr(x, 'field') and hasattr(x.field, 'choices') \
                    and hasattr(x, 'lookup_val') and x.lookup_val:
                if isinstance(x.field, BooleanField):
                    self.append(
                        x.title,
                        _("No") if x.lookup_val == '0' else _("Yes"),
                        x.lookup_kwarg
                    )
                    params.pop(x.lookup_kwarg, None)
                else:
                    choices = dict(x.field.choices)
                    elements = []
                    for i in x.lookup_val.split(','):
                        elements.append(
                            choices[int(i)] if isinstance(x.field, IntegerField) else choices[i]
                        )
                    self.append(x.title, ', '.join(list(map(str, elements))), x.lookup_kwarg)
                    params.pop(x.lookup_kwarg, None)

        # filters no standards
        params.pop("date__gte", None)
        params.pop("date__lt", None)
        for k in params:
            if k.endswith("__id__exact"):
                try:
                    _classname = k.split("__")[-3]
                except IndexError:
                    _classname = k.split("__")[0]
                _name = ugettext(_classname.capitalize())

                if _classname == "ExcludeAttribute":
                    _classname = "deployment"
                    _name = "excluded attributes"
                if _classname == "ExcludedAttributesGroup":
                    _classname = "attributeset"
                    _name = "excluded attributes"
                if _classname == 'sync_attributes':
                    _classname = 'attribute'
                    _name = 'sync attributes'
                if _classname == 'included_attributes':
                    _classname = 'attribute'
                    _name = 'included attributes'
                if _classname == 'excluded_attributes':
                    _classname = 'attribute'
                    _name = 'excluded attributes'

                if not hasattr(self.model, _classname):
                    if _classname == 'attribute':
                        _app = 'server'
                    elif _classname == 'application':
                        _app = 'catalog'
                    else:
                        _app = self.model._meta.app_label
                    model = apps.get_model(_app, _classname)
                    try:
                        self.append(_name, model.objects.get(pk=params[k]), k)
                    except ObjectDoesNotExist:
                        pass
                else:
                    model = getattr(self.model, _classname)
                    _classname = model.field.related_model.__name__
                    _app = model.field.related_model._meta.app_label
                    model = apps.get_model(_app, _classname)
                    try:
                        self.append(_name, model.objects.get(pk=params[k]), k)
                    except ObjectDoesNotExist:
                        pass

            elif k.endswith("id__in"):
                try:
                    _classname = k.split("__")[-3]
                except IndexError:
                    _classname = self.model.__name__
                _name = ugettext(_classname.capitalize())

                if _classname == "ExcludeAttribute":
                    _classname = "deployment"
                    _name = "excluded attributes"
                if _classname == "ExcludedAttributesGroup":
                    _classname = ugettext("attributeset")
                    _name = "excluded attributes"
                if _classname == 'sync_attributes':
                    _classname = 'attribute'
                    _name = 'sync attributes'
                if _classname == 'included_attributes':
                    _classname = 'attribute'
                    _name = 'included attributes'
                if _classname == 'excluded_attributes':
                    _classname = 'attribute'
                    _name = 'excluded attributes'

                _app = self.model._meta.app_label
                model = apps.get_model(_app, _classname)
                _list = []
                for _id in params[k].split(",")[0:10]:  # limit to 10 elements
                    _list.append(
                        model.objects.get(
                            pk=int(_id)
                        ).__str__()
                    )
                self.append(
                    _name,
                    ", ".join(_list) + "..." if len(_list) == 10 else ", ".join(_list),
                    k
                )
            else:
                if k not in remove:
                    try:
                        name, lookup_type = k.split('__')
                        if name == 'updated_at' or name == 'created_at':
                            name = 'date'
                        name = name.replace('_', ' ')
                        if lookup_type == 'isnull':
                            self.append(
                                name,
                                _('empty') if params[k] == 'True' else _('not empty'),
                                k
                            )
                        elif lookup_type == 'lt':
                            self.append(
                                name,
                                '< {}'.format(params[k]),
                                k
                            )
                        elif lookup_type == 'lte':
                            self.append(
                                name,
                                '<= {}'.format(params[k]),
                                k
                            )
                        elif lookup_type == 'gt':
                            self.append(
                                name,
                                '> {}'.format(params[k]),
                                k
                            )
                        elif lookup_type == 'gte':
                            self.append(
                                name,
                                '>= {}'.format(params[k]),
                                k
                            )
                        else:
                            self.append(k, params[k], k)
                    except ValueError:
                        name = k
                        if name == 'q':
                            name = 'search'
                        self.append(name, params[k], k)

        _filter = ", ".join(
            "{}: {}".format(
                k["name"].capitalize(),
                k["value"]
            )
            for k in self.filter_description
        )
        if _filter:
            _filter = "({})".format(_filter)

        self.title = "{} {}".format(
            self.model._meta.verbose_name_plural,
            _filter
        )

    def append(self, name, value, param=None, aux_param=None):
        self.filter_description.append({
            "name": _(name),
            "value": value,
            "param": param,
            "aux_param": aux_param,
        })
