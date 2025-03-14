import React from "react";
import { useParams } from "react-router-dom";

const AuctionDetails = () => {
  const { id } = useParams();

  return (
    <div>
      <h2>Auction Details - ID: {id}</h2>
      <p>Item Name: Sample Item {id}</p>
      <p>Highest Bid: $XXX</p>
      <button>Place Bid</button>
    </div>
  );
};

export default AuctionDetails;
