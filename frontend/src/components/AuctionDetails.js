import React from "react";
import { useParams } from "react-router-dom";

const AuctionDetails = () => {
  const { id } = useParams();

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <div className="bg-white p-6 rounded-lg shadow-lg w-96">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          Auction Details - ID: {id}
        </h2>
        <p className="text-lg text-gray-600">Item Name: Sample Item {id}</p>
        <p className="text-lg text-gray-600">Highest Bid: <span className="font-semibold">$XXX</span></p>
        <button className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition">
          Place Bid
        </button>
      </div>
    </div>
  );
};

export default AuctionDetails;
