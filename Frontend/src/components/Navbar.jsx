export function Navbar({ activePage, items, messages, onNavigate, onNewChat }) {
  const recentQuestions = messages.filter((message) => message.role === 'user').slice(-4)
  return (
    <aside>
      <b className="brand">RELAY<span>•</span></b>
      <button className="new" onClick={onNewChat}>＋ New chat</button>
      <nav>{items.map((item) => (
        <button className={activePage === item ? 'active' : ''} key={item} onClick={() => onNavigate(item)}>{item}</button>
      ))}</nav>
      <div className="recent"><small>RECENT</small>
        {recentQuestions.map((message, index) => <p key={`${message.text}-${index}`}>{message.text}</p>)}</div>
    </aside>
  )
}
