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
    <div>
      <h2>Create Auction</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Item Name:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        <div>
          <label>Starting Bid:</label>
          <input
            type="number"
            value={startingBid}
            onChange={(e) => setStartingBid(e.target.value)}
            required
          />
        </div>
        <button type="submit">Create Auction</button>
      </form>
    </div>
  );
};

export default CreateAuction;
