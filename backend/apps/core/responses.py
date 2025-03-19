from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Custom pagination class with standardized response format"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "message": "Data retrieved successfully",
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                },
            }
        )


def api_response(
    data=None, message="", success=True, status=200, errors=None, headers=None
):
    """
    Standardized API response format

    Args:
        data: The response data
        message: Response message
        success: Success status (True/False)
        status: HTTP status code
        errors: Error details (if any)
        headers: Optional HTTP headers for the response
    """
    response_data = {"success": success, "message": message}

    if data is not None:
        response_data["data"] = data

    if errors is not None:
        response_data["errors"] = errors

    return Response(response_data, status=status, headers=headers)
