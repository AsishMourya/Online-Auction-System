from django.db.models.query import QuerySet


class ApiResponseMixin:
    """Mixin to provide standard API response format"""

    def finalize_response(self, request, response, *args, **kwargs):
        """Wrap API responses in standard format"""
        response = super().finalize_response(request, response, *args, **kwargs)

        if getattr(response, "accepted_renderer", None) and not getattr(
            response, "_is_rendered", False
        ):
            if (
                response.accepted_renderer.format == "api"
                or response.accepted_renderer.format == "json"
            ):
                if isinstance(response.data, dict) and "success" in response.data:
                    return response

                success = 200 <= response.status_code < 300
                message = "Success" if success else "Error"
                errors = None
                data = response.data

                if not success and isinstance(response.data, dict):
                    errors = response.data

                response.data = {
                    "success": success,
                    "message": message,
                    "data": data if success else None,
                }

                if errors:
                    response.data["errors"] = errors

        return response


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
