from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Auction
from django.shortcuts import get_object_or_404

@csrf_exempt
def create_auction(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title")
            starting_bid = data.get("startingBid")

            # Ensure required fields are present
            if not title or starting_bid is None:
                return JsonResponse({"error": "Missing title or starting bid"}, status=400)

            # Create and save auction
            auction = Auction.objects.create(title=title, highest_bid=starting_bid)

            return JsonResponse({
                "message": f"Auction '{auction.title}' created successfully.",
                "id": auction.id,
                "startingBid": auction.highest_bid
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

def auction_detail(request, id):
    auction = get_object_or_404(Auction, id=id)
    return JsonResponse({
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "highest_bid": auction.highest_bid
    })
