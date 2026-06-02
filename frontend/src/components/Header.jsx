export default function Header({ title }) {
  return (
    <header className="h-14 bg-gray-800 border-b border-gray-700 flex items-center
      justify-between px-6">
      <h1 className="text-white font-medium text-base">{title}</h1>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
        <span className="text-gray-400 text-sm">System live</span>
      </div>
    </header>
  )
}