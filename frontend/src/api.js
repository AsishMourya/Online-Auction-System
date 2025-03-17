const API_BASE_URL = "http://127.0.0.1:8000"; // Django backend

export const fetchAuctions = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auctions/`);
    if (!response.ok) {
      throw new Error("Failed to fetch auctions");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching auctions:", error);
    return [];
  }
};
