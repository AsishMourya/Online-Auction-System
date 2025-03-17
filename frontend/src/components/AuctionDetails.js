import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000/auctions";

const AuctionDetails = () => {
  const { id } = useParams();
  const [auction, setAuction] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAuctionDetails = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/${id}/`);
        if (!response.ok) throw new Error("Auction not found");
        const data = await response.json();
        setAuction(data);
      } catch (error) {
        console.error("Error fetching auction:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAuctionDetails();
  }, [id]);

  if (loading) {
    return <p className="text-center text-lg text-gray-600">Loading...</p>;
  }

  if (!auction) {
    return <p className="text-center text-red-600">Auction not found</p>;
  }

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <div className="bg-white p-6 rounded-lg shadow-lg w-96">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">{auction.title}</h2>
        <p className="text-lg text-gray-600">Description: {auction.description}</p>
        <p className="text-lg text-gray-600">
          Highest Bid: <span className="font-semibold">${auction.highest_bid}</span>
        </p>
        <button className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition">
          Place Bid
        </button>
      </div>
    </div>
  );
};

export default AuctionDetails;
