import React from "react";
import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav className="bg-blue-600 p-4 text-white flex justify-between items-center shadow-md">
      <Link to="/" className="text-xl font-bold">Auction House</Link>
      <div className="space-x-4">
        <Link to="/create" className="hover:underline">Create Auction</Link>
        <Link to="/profile" className="hover:underline">👤 Profile</Link>
      </div>
    </nav>
  );
};

export default Navbar;
