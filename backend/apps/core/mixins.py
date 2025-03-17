from django.db.models.query import QuerySet


class SwaggerSchemaMixin:
    """
    A mixin to handle Swagger schema generation gracefully.
    Returns empty querysets when the view is being examined by Swagger.
    """

    @property
    def is_swagger_request(self):
        """
        Check if the current request is for Swagger schema generation.
        """
        return getattr(self, "swagger_fake_view", False)

    def get_swagger_empty_queryset(self):
        """
        Return an empty queryset of the appropriate type.
        """
        if hasattr(self, "queryset") and self.queryset is not None:
            return self.queryset.model.objects.none()
        return QuerySet().none()
