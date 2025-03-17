import React, { useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000/auctions"; // Django backend URL

const CreateAuction = () => {
  const [title, setTitle] = useState("");
  const [startingBid, setStartingBid] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Convert startingBid to a number
    const bidValue = parseFloat(startingBid);
    if (isNaN(bidValue) || bidValue < 0) {
      setMessage("Starting bid must be a valid positive number.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/create/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, startingBid: bidValue }),
      });

      const data = await response.json();
      if (response.ok) {
        setMessage(`Auction "${data.message}" created successfully!`);
        setTitle("");
        setStartingBid("");
      } else {
        setMessage(data.error);
      }
    } catch (error) {
      setMessage("Failed to create auction.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">
          Create Auction
        </h2>
        {message && (
          <p
            className={`text-center text-sm ${
              message.includes("successfully") ? "text-green-600" : "text-red-600"
            }`}
          >
            {message}
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700">Item Name:</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring focus:ring-blue-400"
            />
          </div>
          <div>
            <label className="block text-gray-700">Starting Bid ($):</label>
            <input
              type="number"
              value={startingBid}
              onChange={(e) => setStartingBid(e.target.value)}
              required
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring focus:ring-blue-400"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
          >
            Create Auction
          </button>
        </form>
      </div>
    </div>
  );
};

export default CreateAuction;
