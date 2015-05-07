# -*- coding: utf-8 -*-

from django.db.models import Q
from django.utils.html import escape

from ajax_select import LookupChannel

from migasfree.server.models import (
    Attribute,
    Package,
    Property,
    DeviceLogical,
    user_version,
    Computer
)


class AttributeLookup(LookupChannel):
    model = Attribute

    def get_query(self, q, request):
        prps = Property.objects.all().values_list('prefix', flat=True)
        if q[0:Property.PREFIX_LEN].upper() in (prop.upper() for prop in prps) \
        and len(q) > (Property.PREFIX_LEN + 1):
            return Attribute.objects.filter(
                Q(property_att__prefix__icontains=q[0:Property.PREFIX_LEN])
            ).filter(Q(value__icontains=q[Property.PREFIX_LEN + 1:])).order_by(
                'value'
            )
        else:
            return Attribute.objects.filter(
                Q(value__icontains=q) | Q(description__icontains=q)
                | Q(property_att__prefix__icontains=q)
            ).order_by('value')

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s-%s %s" % (
            escape(obj.property_att.prefix),
            escape(obj.value),
            escape(obj.description)
        )

    def can_add(self, user, model):
        return False

    def get_objects(self, ids):
        return Attribute.objects.filter(pk__in=ids).order_by(
            'property_att',
            'value'
        )


class Attribute_ComputersLookup(LookupChannel):
    model = Attribute

    def get_query(self, q, request):
        prps = Property.objects.all().values_list('prefix', flat=True)
        if q[0:Property.PREFIX_LEN].upper() in (prop.upper() for prop in prps) \
        and len(q) > (Property.PREFIX_LEN + 1):
            return Attribute.objects.filter(
                Q(property_att__prefix__icontains=q[0:Property.PREFIX_LEN])
            ).filter(Q(value__icontains=q[Property.PREFIX_LEN + 1:])).order_by(
                'value'
            )
        else:
            return Attribute.objects.filter(
                Q(value__icontains=q) | Q(description__icontains=q)
                | Q(property_att__prefix__icontains=q)
            ).order_by('value')

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s-%s %s (%s)" % (
            escape(obj.property_att.prefix),
            escape(obj.value),
            escape(obj.description),
            escape(obj.total_computers(user_version()))
        )

    def can_add(self, user, model):
        return False

    def get_objects(self, ids):
        return Attribute.objects.filter(pk__in=ids).order_by(
            'property_att',
            'value'
        )


class PackageLookup(LookupChannel):
    model = Package

    def get_query(self, q, request):
        return Package.objects.filter(Q(name__icontains=q)).order_by('name')

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s" % escape(obj.name)

    def can_add(self, user, model):
        return False

    def get_objects(self, ids):
        return Package.objects.filter(pk__in=ids).order_by('name')


class TagLookup(LookupChannel):
    model = Attribute

    def get_query(self, q, request):
        return Attribute.objects.filter(
            property_att__active=True).filter(
            property_att__tag=True).filter(
            Q(value__icontains=q) | Q(description__icontains=q)
            | Q(property_att__prefix__icontains=q)
        ).order_by('value')

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s-%s %s" % (
            escape(obj.property_att.prefix),
            escape(obj.value),
            escape(obj.description)
        )

    def can_add(self, user, model):
        return False

    def get_objects(self, ids):
        return Attribute.objects.filter(pk__in=ids).order_by(
            'property_att',
            'value'
        )


class DeviceLogicalLookup(LookupChannel):
    model = DeviceLogical

    def get_query(self, q, request):
        return DeviceLogical.objects.filter(Q(device__name__icontains=q))

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s" % escape(obj.__str__())

    def can_add(self, user, model):
        return False


class ComputerLookup(LookupChannel):
    model = Computer

    def get_query(self, q, request):
        return Computer.objects.filter(Q(name__icontains=q) | Q(id=q))

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return u"%s" % escape(obj.__unicode__())

    def can_add(self, user, model):
        return False

    def get_objects(self, ids):
        """
        Get the currently selected objects when editing an existing model
        """
        # return in the same order as passed in here
        # this will be however the related objects Manager returns them
        # which is not guaranteed to be the same order
        # they were in when you last edited
        # see OrdredManyToMany.md
        lst = []
        for id in ids:
            if id.__class__.__name__ == "Computer":
                lst.append(int(id.pk))
            else:
                lst.append(int(id))

        things = self.model.objects.in_bulk(lst)

        return [things[aid] for aid in lst if aid in things]
