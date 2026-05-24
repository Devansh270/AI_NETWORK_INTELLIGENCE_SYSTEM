import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <div className="w-64 h-screen bg-gray-900 text-white p-5">
      <h1 className="text-2xl font-bold mb-8">
        AI Network System
      </h1>

      <nav className="flex flex-col gap-4">
        <Link to="/" className="hover:text-blue-400">
          Dashboard
        </Link>

        <Link to="/topology" className="hover:text-blue-400">
          Topology
        </Link>

        <Link to="/alerts" className="hover:text-blue-400">
          Alerts
        </Link>

        <Link to="/routing" className="hover:text-blue-400">
          Routing
        </Link>
      </nav>
    </div>
  );
}