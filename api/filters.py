import django_filters
from .models import Vehicle, SafariPackage

class VehicleFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="daily_rate", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="daily_rate", lookup_expr='lte')
    min_seats = django_filters.NumberFilter(field_name="seats", lookup_expr='gte')
    max_seats = django_filters.NumberFilter(field_name="seats", lookup_expr='lte')
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='iexact')
    available_on = django_filters.DateFilter(method='filter_available_on')

    class Meta:
        model = Vehicle
        fields = ['category', 'min_price', 'max_price', 'min_seats', 'max_seats', 'available_on']

    def filter_available_on(self, queryset, name, value):
        # exclude vehicles that have an availability record showing booked on that date
        return queryset.exclude(availabilities__date=value, availabilities__is_booked=True)


class SafariFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="base_price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="base_price", lookup_expr='lte')
    region = django_filters.CharFilter(field_name='region', lookup_expr='iexact')
    min_duration = django_filters.NumberFilter(field_name='duration_days', lookup_expr='gte')
    max_duration = django_filters.NumberFilter(field_name='duration_days', lookup_expr='lte')

    class Meta:
        model = SafariPackage
        fields = ['region', 'min_price', 'max_price', 'min_duration', 'max_duration']
