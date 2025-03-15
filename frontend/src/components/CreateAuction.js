import React, { useState } from "react";

const CreateAuction = () => {
  const [title, setTitle] = useState("");
  const [startingBid, setStartingBid] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("New Auction:", { title, startingBid });
    setTitle("");
    setStartingBid("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">
          Create Auction
        </h2>
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