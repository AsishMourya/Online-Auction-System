import React from "react";
import { Link } from "react-router-dom";

const Home = () => {

  const auctions = [
    { id: 1, title: "Bat", highestBid: "2500", image: "https://c8.alamy.com/comp/BH8C6P/cricket-bat-BH8C6P.jpg" },
    { id: 2, title: "Ball", highestBid: "30", image: "https://nwscdn.com/media/catalog/product/cache/h700xw700/r/e/redfortressball-main.jpg" },
    { id: 3, title: "Wickets", highestBid: "600", image: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQah1yb5V-Q9dKjkLt4gRq44M5tegDYRep4kQ&s" },
  ];

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-6">Live Auctions</h1>

        <div className="grid md:grid-cols-3 gap-6">
          {auctions.map((auction) => (
            <div key={auction.id} className="bg-white rounded-lg shadow-lg overflow-hidden">
              <img src={auction.image} alt={auction.title} className="w-full h-40 object-cover" />
              <div className="p-4">
                <h2 className="text-lg font-semibold text-gray-800">{auction.title}</h2>
                <p className="text-gray-600">Current Bid: <span className="font-bold">{auction.highestBid}</span></p>
                <Link 
                  to={`/auction/${auction.id}`} 
                  className="block text-center mt-3 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  View Auction
                </Link>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-center mt-8">
          <Link 
            to="/create" 
            className="bg-green-600 text-white text-lg px-6 py-3 rounded-lg shadow-md hover:bg-green-700 transition"
          >
            Create New Auction
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Home;
