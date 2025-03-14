import React from "react";
import { Link } from "react-router-dom";

const Home = () => {
  // Placeholder auction data
  const auctions = [
    { id: 1, title: "Antique Vase", highestBid: "$120" },
    { id: 2, title: "Rare Comic Book", highestBid: "$450" },
  ];

  return (
    <div>
      <h1>Live Auctions</h1>
      <ul>
        {auctions.map((auction) => (
          <li key={auction.id}>
            <Link to={`/auction/${auction.id}`}>
              {auction.title} - Current Bid: {auction.highestBid}
            </Link>
          </li>
        ))}
      </ul>
      <Link to="/create">Create New Auction</Link>
    </div>
  );
};

export default Home;
