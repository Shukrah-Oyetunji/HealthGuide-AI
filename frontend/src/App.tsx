
import { useEffect, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  getHealthInterests,
  saveHealthInterests,
  getQuestionHistory,
  askHealthQuestion,
  getHealthLibrary,
  getLibraryQuestion,
  type User,
  type AskResponse,
  type LibraryItem,
  type LibraryQuestionDetail,
} from './services/api'
import {
  Activity,
  ArrowRight,
  BookOpen,
  Check,
  CircleHelp,
  Clock3,
  FileText,
  HeartPulse,
  Menu,
  MessageCircle,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
} from 'lucide-react'
import './App.css'
import './Auth.css'

type AuthMode = 'login' | 'register'

type Topic = {
  title: string
  description: string
  prompt: string
  icon: typeof Activity
}

type RecentTopic = {
  question: string
  date: string
}

type ChatMessage = {
  id: string | number
  role: 'user' | 'assistant'
  content: string
  response?: AskResponse
}

const topics: Topic[] = [
  {
    icon: Activity,
    title: 'Understanding diabetes',
    description: 'Types, common risk factors and general health information.',
    prompt: 'What is diabetes, and what are its common types?',
  },
  {
    icon: ShieldCheck,
    title: 'Malaria prevention',
    description: 'Learn about general public-health prevention guidance.',
    prompt: 'What are some general ways to prevent malaria?',
  },
  {
    icon: HeartPulse,
    title: 'Heart health basics',
    description: 'Explore factors that can affect cardiovascular health.',
    prompt: 'What factors can affect heart health?',
  },
  {
    icon: BookOpen,
    title: 'Healthy everyday habits',
    description: 'Explore everyday health education topics.',
    prompt: 'What are some general habits that support good health?',
  },
]

const interestOptions = [
  'General wellness',
  'Nutrition',
  'Infectious diseases',
  'Heart health',
  'Public health',
  'Mental wellbeing',
  'Maternal and child health',
  'Chronic conditions',
]

// ---------------------------------------------------------
// AUTHENTICATION PANEL
// ---------------------------------------------------------

type AuthPanelProps = {
  mode: AuthMode
  notice: string
  onSwitch: (mode: AuthMode, notice?: string) => void
  onBack: () => void
  onLogin: (user: User) => void
}

function AuthPanel({
  mode,
  notice,
  onSwitch,
  onBack,
  onLogin,
}: AuthPanelProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const isRegister = mode === 'register'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        await registerUser({
          name: name.trim(),
          email: email.trim(),
          password,
        })

        onSwitch('login', 'Account created successfully. Please sign in.')
      } else {
        const result = await loginUser({
          email: email.trim(),
          password,
        })

        onLogin(result.user)
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <button className="auth-back" type="button" onClick={onBack}>
          ← Back to HealthGuide
        </button>

        <div className="auth-brand-mark">
          <HeartPulse size={27} />
        </div>

        <p className="auth-eyebrow">HEALTHGUIDE AI</p>

        <h1>{isRegister ? 'Create your account' : 'Welcome back'}</h1>

        <p className="auth-description">
          {isRegister
            ? 'Create an account to start your personal health-learning space.'
            : 'Sign in to continue to your HealthGuide dashboard.'}
        </p>

        {notice && (
          <div className="auth-success" role="status">
            {notice}
          </div>
        )}

        {error && (
          <div className="auth-error" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister && (
            <label>
              Full name
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                minLength={2}
                maxLength={100}
                autoComplete="name"
                required
              />
            </label>
          )}

          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={
                isRegister ? 'At least 8 characters' : 'Enter your password'
              }
              minLength={isRegister ? 8 : 1}
              maxLength={128}
              autoComplete={
                isRegister ? 'new-password' : 'current-password'
              }
              required
            />
          </label>

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading
              ? 'Please wait...'
              : isRegister
                ? 'Create account'
                : 'Sign in'}

            {!loading && <ArrowRight size={17} />}
          </button>
        </form>

        <p className="auth-switch">
          {isRegister
            ? 'Already have an account?'
            : "Don't have an account?"}{' '}
          <button
            type="button"
            onClick={() => onSwitch(isRegister ? 'login' : 'register')}
          >
            {isRegister ? 'Sign in' : 'Create account'}
          </button>
        </p>

        <p className="auth-safety">
          <ShieldCheck size={15} />
          Health education, not diagnosis or treatment.
        </p>
      </section>
    </main>
  )
}

// ---------------------------------------------------------
// MARKDOWN ANSWER RENDERER
// ---------------------------------------------------------

type AnswerMarkdownProps = {
  content: string
}

function AnswerMarkdown({ content }: AnswerMarkdownProps) {
  return (
    <div className="answer-markdown">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}

// ---------------------------------------------------------
// MAIN APPLICATION
// ---------------------------------------------------------

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<AuthMode | null>(null)
  const [authNotice, setAuthNotice] = useState('')
  const [activeNav, setActiveNav] = useState('Dashboard')
  const [question, setQuestion] = useState('')
  const [showMenu, setShowMenu] = useState(false)
  const [showAbout, setShowAbout] = useState(false)

  // Dashboard state
  const [interests, setInterests] = useState<string[]>([])
  const [recentTopics, setRecentTopics] = useState<RecentTopic[]>([])
  const [profileError, setProfileError] = useState('')
  const [savingInterests, setSavingInterests] = useState(false)

  // AI chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatError, setChatError] = useState('')
  const [loadingAnswer, setLoadingAnswer] = useState(false)

  // Health Library state
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([])
  const [selectedLibraryQuestion, setSelectedLibraryQuestion] =
    useState<LibraryQuestionDetail | null>(null)
  const [librarySearch, setLibrarySearch] = useState('')
  const [selectedTopic, setSelectedTopic] = useState('All topics')
  const [libraryLoading, setLibraryLoading] = useState(false)
  const [libraryDetailLoading, setLibraryDetailLoading] = useState(false)
  const [libraryError, setLibraryError] = useState('')

  // -------------------------------------------------------
  // RESTORE SIGNED-IN USER
  // -------------------------------------------------------

  useEffect(() => {
    if (!localStorage.getItem('healthguide_token')) return

    getCurrentUser()
      .then(setCurrentUser)
      .catch(() => {
        logoutUser()
        setCurrentUser(null)
      })
  }, [])

  // -------------------------------------------------------
  // LOAD DASHBOARD DATA
  // -------------------------------------------------------

  useEffect(() => {
    if (!currentUser) {
      setInterests([])
      setRecentTopics([])
      setMessages([])
      setProfileError('')
      return
    }

    let cancelled = false

    setProfileError('')

    Promise.all([getHealthInterests(), getQuestionHistory()])
      .then(([savedInterests, history]) => {
        if (cancelled) return

        setInterests(savedInterests)

        setRecentTopics(
          history
            .map((item) => ({
              question: item.question,
              date: new Date(item.created_at).toLocaleDateString(),
            }))
            .slice(0, 5),
        )
      })
      .catch((error) => {
        if (cancelled) return

        setProfileError(
          error instanceof Error
            ? error.message
            : 'Could not load your saved profile data.',
        )
      })

    return () => {
      cancelled = true
    }
  }, [currentUser])

  // -------------------------------------------------------
  // LOAD HEALTH LIBRARY
  // -------------------------------------------------------

  useEffect(() => {
    if (!currentUser || activeNav !== 'Health library') return

    let cancelled = false

    async function loadLibrary() {
      setLibraryLoading(true)
      setLibraryError('')

      try {
        const records = await getHealthLibrary()

        if (!cancelled) {
          setLibraryItems(records)
        }
      } catch (error) {
        if (!cancelled) {
          setLibraryError(
            error instanceof Error
              ? error.message
              : 'Could not load your Health Library.',
          )
        }
      } finally {
        if (!cancelled) {
          setLibraryLoading(false)
        }
      }
    }

    void loadLibrary()

    return () => {
      cancelled = true
    }
  }, [currentUser, activeNav])

  // -------------------------------------------------------
  // NAVIGATION
  // -------------------------------------------------------

  function startQuestion(value = '') {
    setQuestion(value)
    setActiveNav('Ask HealthGuide')
    setShowMenu(false)
    setChatError('')
  }

  // -------------------------------------------------------
  // DASHBOARD INTERESTS
  // -------------------------------------------------------

  async function toggleInterest(interest: string, checked: boolean) {
    const previous = interests

    const next = checked
      ? [...previous, interest]
      : previous.filter((item) => item !== interest)

    setInterests(next)
    setSavingInterests(true)
    setProfileError('')

    try {
      const result = await saveHealthInterests(next)
      setInterests(result.interests)
    } catch (error) {
      setInterests(previous)

      setProfileError(
        error instanceof Error
          ? error.message
          : 'Could not save your interests.',
      )
    } finally {
      setSavingInterests(false)
    }
  }

  // -------------------------------------------------------
  // SUBMIT HEALTH QUESTION
  // -------------------------------------------------------

  async function submitQuestion(value: string) {
    const trimmed = value.trim()

    if (!trimmed || loadingAnswer) return

    setChatError('')
    setProfileError('')
    setQuestion('')
    setLoadingAnswer(true)
    setActiveNav('Ask HealthGuide')

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    }

    setMessages((current) => [...current, userMessage])

    try {
      // /api/ask retrieves evidence, generates the answer,
      // and saves the question and answer in the database.
      const result = await askHealthQuestion(trimmed)

      const assistantMessage: ChatMessage = {
        id: `assistant-${result.question_id}`,
        role: 'assistant',
        content: result.answer,
        response: result,
      }

      setMessages((current) => [...current, assistantMessage])

      setRecentTopics((current) =>
        [
          {
            question: trimmed,
            date: new Date().toLocaleDateString(),
          },
          ...current.filter((item) => item.question !== trimmed),
        ].slice(0, 5),
      )

      // Refresh recent topics from the backend.
      try {
        const history = await getQuestionHistory()

        setRecentTopics(
          history
            .map((item) => ({
              question: item.question,
              date: new Date(item.created_at).toLocaleDateString(),
            }))
            .slice(0, 5),
        )
      } catch {
        // Keep the recently added question if history refresh fails.
      }
    } catch (error) {
      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to get an answer. Please try again.',
      )
    } finally {
      setLoadingAnswer(false)
    }
  }

  // -------------------------------------------------------
  // HEALTH LIBRARY: OPEN SAVED QUESTION
  // -------------------------------------------------------

  async function openLibraryQuestion(questionId: number) {
    setLibraryDetailLoading(true)
    setLibraryError('')
    setSelectedLibraryQuestion(null)

    try {
      const detail = await getLibraryQuestion(questionId)
      setSelectedLibraryQuestion(detail)
    } catch (error) {
      setLibraryError(
        error instanceof Error
          ? error.message
          : 'Could not load this saved answer.',
      )
    } finally {
      setLibraryDetailLoading(false)
    }
  }

  // -------------------------------------------------------
  // HEALTH LIBRARY: FILTERS
  // -------------------------------------------------------

  const libraryTopics = [
    'All topics',
    ...Array.from(
      new Set(
        libraryItems
          .map((item) => item.topic || 'General Health')
          .filter(Boolean),
      ),
    ).sort(),
  ]

  const filteredLibraryItems = libraryItems.filter((item) => {
    const matchesTopic =
      selectedTopic === 'All topics' ||
      (item.topic || 'General Health') === selectedTopic

    const matchesSearch = item.question
      .toLowerCase()
      .includes(librarySearch.trim().toLowerCase())

    return matchesTopic && matchesSearch
  })

  // -------------------------------------------------------
  // CHAT CONTROLS
  // -------------------------------------------------------

  function clearChat() {
    if (loadingAnswer) return

    setMessages([])
    setQuestion('')
    setChatError('')
  }

  // -------------------------------------------------------
  // SIGN OUT
  // -------------------------------------------------------

  function signOut() {
    logoutUser()
    setCurrentUser(null)
    setAuthMode(null)
    setAuthNotice('')
    setActiveNav('Dashboard')
    setQuestion('')
    setMessages([])
    setChatError('')
    setLibraryItems([])
    setSelectedLibraryQuestion(null)
    setLibrarySearch('')
    setSelectedTopic('All topics')
    setLibraryError('')
    setShowMenu(false)
  }

  // -------------------------------------------------------
  // AUTHENTICATION SCREEN
  // -------------------------------------------------------

  if (authMode) {
    return (
      <AuthPanel
        mode={authMode}
        notice={authNotice}
        onSwitch={(mode, notice = '') => {
          setAuthMode(mode)
          setAuthNotice(notice)
        }}
        onBack={() => {
          setAuthMode(null)
          setAuthNotice('')
        }}
        onLogin={(user) => {
          setCurrentUser(user)
          setAuthMode(null)
          setAuthNotice('')
          setActiveNav('Dashboard')
        }}
      />
    )
  }

  // -------------------------------------------------------
  // PUBLIC LANDING PAGE
  // -------------------------------------------------------

  if (!currentUser) {
    return (
      <main className="public-landing">
        <header className="landing-nav">
          <a
            className="brand"
            href="#"
            onClick={(e) => e.preventDefault()}
          >
            <span className="brand-mark">
              <HeartPulse size={23} />
            </span>
            <span className="brand-copy">
              <strong>HealthGuide</strong>
              <span>AI HEALTH ASSISTANT</span>
            </span>
          </a>

          <div className="landing-actions">
            <button
              className="landing-signin"
              onClick={() => {
                setAuthNotice('')
                setAuthMode('login')
              }}
            >
              Sign in
            </button>

            <button
              className="primary-button"
              onClick={() => {
                setAuthNotice('')
                setAuthMode('register')
              }}
            >
              Get started <ArrowRight size={16} />
            </button>
          </div>
        </header>

        <section className="landing-hero">
          <span className="welcome-badge">
            <span className="welcome-badge-icon">
              <ShieldCheck size={14} />
            </span>
            PUBLIC HEALTH, MADE CLEARER
          </span>

          <h1>
            Understand health information.
            <br />
            <span>Know where it comes from.</span>
          </h1>

          <p>
            HealthGuide AI makes public-health information easier to
            understand, using retrieved information from health sources and
            transparent evidence.
          </p>

          <div className="landing-hero-actions">
            <button
              className="primary-button"
              onClick={() => {
                setAuthNotice('')
                setAuthMode('register')
              }}
            >
              Create your free account <ArrowRight size={17} />
            </button>
          </div>

          <div className="landing-note">
            <Sparkles size={17} />
            <span>
              <strong>Health information assistant.</strong> Answers are
              generated from retrieved evidence where available. Always
              consult a qualified health professional for personal medical
              concerns.
            </span>
          </div>
        </section>

        <section className="landing-topics">
          <div className="suggestion-heading">
            <div>
              <span className="section-kicker">EXPLORE HEALTH EDUCATION</span>
              <h2>Topics the assistant is designed to support</h2>
            </div>
          </div>

          <div className="suggestion-grid">
            {topics.map((item) => {
              const Icon = item.icon

              return (
                <article
                  className="suggestion-card landing-topic"
                  key={item.title}
                >
                  <span className="suggestion-icon">
                    <Icon size={19} />
                  </span>
                  <span className="suggestion-title">{item.title}</span>
                  <span className="suggestion-description">
                    {item.description}
                  </span>
                </article>
              )
            })}
          </div>
        </section>

        <footer className="landing-footer">
          <span>© 2026 HealthGuide AI</span>
          <span>Health education, not diagnosis or treatment.</span>
          <button onClick={() => setShowAbout(true)}>
            About this project <ArrowRight size={13} />
          </button>
        </footer>

        {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
      </main>
    )
  }

  // -------------------------------------------------------
  // SIGNED-IN APPLICATION
  // -------------------------------------------------------

  return (
    <div className="app-shell">
      <aside className={`sidebar ${showMenu ? 'sidebar-open' : ''}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault()
            setActiveNav('Dashboard')
            setShowMenu(false)
          }}
        >
          <span className="brand-mark">
            <HeartPulse size={23} />
          </span>
          <span className="brand-copy">
            <strong>HealthGuide</strong>
            <span>AI HEALTH ASSISTANT</span>
          </span>
        </a>

        <button
          className="new-chat-button"
          onClick={() => {
            clearChat()
            startQuestion()
          }}
          disabled={loadingAnswer}
        >
          <Plus size={18} /> New chat
        </button>

        <div className="sidebar-label">YOUR WORKSPACE</div>

        <nav className="side-nav">
          <button
            className={`nav-item ${activeNav === 'Dashboard' ? 'active' : ''}`}
            onClick={() => {
              setActiveNav('Dashboard')
              setShowMenu(false)
            }}
          >
            <UserRound size={18} /> Dashboard
          </button>

          <button
            className={`nav-item ${activeNav === 'Ask HealthGuide' ? 'active' : ''}`}
            onClick={() => startQuestion()}
          >
            <MessageCircle size={18} /> Ask HealthGuide
          </button>

          <button
            className={`nav-item ${activeNav === 'Health library' ? 'active' : ''}`}
            onClick={() => {
              setActiveNav('Health library')
              setShowMenu(false)
            }}
          >
            <BookOpen size={18} /> Health library
          </button>

          <button
            className={`nav-item ${activeNav === 'How it works' ? 'active' : ''}`}
            onClick={() => {
              setActiveNav('How it works')
              setShowMenu(false)
            }}
          >
            <CircleHelp size={18} /> How it works
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="privacy-card">
            <span className="privacy-icon">
              <ShieldCheck size={19} />
            </span>
            <strong>Evidence matters</strong>
            <p>
              Answers cite retrieved sources and should be clear about
              evidence limits.
            </p>
          </div>
        </div>
      </aside>

      {showMenu && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={() => setShowMenu(false)}
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu-button"
              aria-label="Open navigation"
              onClick={() => setShowMenu(true)}
            >
              <Menu size={20} />
            </button>

            <div className="breadcrumb">
              {/* <span>Workspace</span> */}
              {/* <span className="breadcrumb-slash">/</span> */}
              <strong>{activeNav}</strong>
            </div>
          </div>

          <div className="topbar-right">
            <span className="account-name">{currentUser.name}</span>
            <button className="auth-top-button" onClick={signOut}>
              Sign out
            </button>
            <div className="avatar">
              {currentUser.name.slice(0, 2).toUpperCase()}
            </div>
          </div>
        </header>

        {/* -----------------------------------------------
            DASHBOARD
        ------------------------------------------------ */}

        {activeNav === 'Dashboard' ? (
          <section className="dashboard-page">
            <div className="dashboard-welcome">
              <div>
                <span className="eyebrow">
                  <Sparkles size={15} /> YOUR HEALTH LEARNING SPACE
                </span>
                <h1>Welcome, {currentUser.name.split(' ')[0]}.</h1>
                <p>
                  Choose what you would like to learn about, or start with a
                  general health question.
                </p>
              </div>

              {/* <div className="dashboard-welcome-icon">
                <HeartPulse size={32} />
              </div> */}
            </div>

            <div className="dashboard-primary-card">
              <div className="dashboard-primary-icon">
                <MessageCircle size={23} />
              </div>
              <div>
                <span className="section-kicker">READY WHEN YOU ARE</span>
                <h2>What would you like to understand today?</h2>
                <p>
                  Ask a public-health question and receive an AI-generated
                  response.
                </p>
              </div>
              <button
                className="primary-button"
                onClick={() => startQuestion()}
              >
                Ask a question <ArrowRight size={16} />
              </button>
            </div>

            {profileError && (
              <div className="auth-error" role="alert">
                {profileError}
              </div>
            )}

            <div className="dashboard-columns">
              <section className="dashboard-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Your learning interests</h2>
                  </div>
                  <span className="panel-count">
                    {interests.length} selected
                  </span>
                </div>

                <p className="panel-description">
                  Choose topics you are interested in.
                </p>

                <div className="interest-list">
                  {interestOptions.map((item) => (
                    <label
                      className={`interest-chip ${
                        interests.includes(item) ? 'selected' : ''
                      }`}
                      key={item}
                    >
                      <input
                        type="checkbox"
                        checked={interests.includes(item)}
                        onChange={(e) =>
                          void toggleInterest(item, e.target.checked)
                        }
                        disabled={savingInterests}
                      />
                      <span>{item}</span>
                      {interests.includes(item) && <Check size={14} />}
                    </label>
                  ))}
                </div>

                {savingInterests && (
                  <p className="panel-description">
                    Saving your interests...
                  </p>
                )}
              </section>

              <section className="dashboard-panel">
                <div className="panel-heading">
                  <div>
                    <h2>YOUR ACTIVITIES</h2>
                  </div>
                  <Clock3 size={18} />
                </div>

                {recentTopics.length ? (
                  <div className="recent-list">
                    {recentTopics.map((item, index) => (
                      <button
                        className="recent-topic"
                        key={`${item.question}-${index}`}
                        onClick={() => startQuestion(item.question)}
                      >
                        <span className="recent-topic-icon">
                          <MessageCircle size={16} />
                        </span>
                        <span>
                          <strong>{item.question}</strong>
                          <small>{item.date}</small>
                        </span>
                        <ArrowRight size={15} />
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="recent-empty">
                    <div className="empty-icon">
                      <Clock3 size={21} />
                    </div>
                    <strong>No recent topics yet</strong>
                    <p>
                      Your questions will appear here after you start exploring.
                    </p>
                    <button
                      className="text-button"
                      onClick={() => startQuestion()}
                    >
                      Ask your first question <ArrowRight size={14} />
                    </button>
                  </div>
                )}
              </section>
            </div>

            <div className="dashboard-safety">
              <ShieldCheck size={18} />
              <span>
                <strong>Designed for health education.</strong> HealthGuide AI
                provides general information, not diagnosis or treatment.
                Consult a qualified health professional about personal health
                concerns.
              </span>
            </div>
          </section>

        /* -----------------------------------------------
            ASK HEALTHGUIDE
        ------------------------------------------------ */

        ) : activeNav === 'Ask HealthGuide' ? (
          <section className="chat-page">
            <div className="conversation conversation-ready">
              <div className="conversation-heading">
                <div>
                  {/* <span className="section-kicker">
                    PUBLIC HEALTH EDUCATION
                  </span> */}
                  <h1>Ask HealthGuide</h1>
                </div>
                <button
                  className="text-button"
                  onClick={clearChat}
                  disabled={loadingAnswer}
                >
                  <Plus size={16} /> New chat
                </button>
              </div>

              {messages.length === 0 && (
                <>
                  <div className="chat-empty-state">
                    {/* <div className="empty-icon">
                      <HeartPulse size={25} />
                    </div> */}
                    <h2>
                      How can I help you understand health information?
                    </h2>
                    <p>
                      Ask a general health question. HealthGuide will search
                      available health information and provide an answer with
                      sources where evidence is available.
                    </p>
                  </div>

                  <div className="question-service-notice">
                    <ShieldCheck size={19} />
                    <div>
                      <strong>Evidence-based health information</strong>
                      <p>
                        Responses are for education and are not a substitute
                        for professional medical advice, diagnosis or treatment.
                      </p>
                    </div>
                  </div>
                </>
              )}

              {messages.map((message, index) => (
                <article
                  className={`chat-message ${
                    message.role === 'user'
                      ? 'user-message'
                      : 'assistant-message'
                  }`}
                  key={`${message.id}-${index}`}
                >
                  <span className="message-author">
                    {message.role === 'user' ? 'You' : 'HealthGuide AI'}
                  </span>

                  <AnswerMarkdown content={message.content} />

                  {message.role === 'assistant' &&
                    message.response?.sources?.length ? (
                      <div className="answer-sources">
                        <strong>
                          Sources ({message.response.sources.length})
                        </strong>

                        <ul>
                          {message.response.sources.map((source) => (
                            <li key={source.id}>
                              {source.url ? (
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {source.title || 'Health information source'}
                                  <span> ↗</span>
                                </a>
                              ) : (
                                <strong>
                                  {source.title || 'Health information source'}
                                </strong>
                              )}

                              <br />
                              <small>
                                {source.source}
                                {source.page !== null &&
                                source.page !== undefined
                                  ? ` · Page ${source.page}`
                                  : ''}
                              </small>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                  {message.role === 'assistant' &&
                    message.response &&
                    !message.response.has_evidence && (
                      <p className="message-footnote">
                        The available sources did not provide sufficient
                        supporting evidence for this question.
                      </p>
                    )}
                </article>
              ))}

              {loadingAnswer && (
                <div className="assistant-loading" role="status">
                  <Sparkles size={17} />
                  <span>
                    HealthGuide is searching health sources and preparing
                    your answer...
                  </span>
                </div>
              )}

              {chatError && (
                <div className="auth-error" role="alert">
                  {chatError}
                </div>
              )}

              <div className="question-composer">
                <label htmlFor="health-question">
                  What would you like to understand?
                </label>

                <textarea
                  id="health-question"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      void submitQuestion(question)
                    }
                  }}
                  placeholder="Ask a general health-information question..."
                  rows={3}
                  disabled={loadingAnswer}
                />

                <div className="composer-bottom">
                  <button
                    className="send-button"
                    onClick={() => void submitQuestion(question)}
                    disabled={!question.trim() || loadingAnswer}
                  >
                    {loadingAnswer ? 'Generating...' : 'Send question'}
                    <Send size={15} />
                  </button>
                </div>
              </div>

              {messages.length === 0 && (
                <>
                  <div className="suggestion-heading">
                    <div>
                      <h2>Explore a topics</h2>
                    </div>
                  </div>

                  <div className="suggestion-grid">
                    {topics.map((item) => {
                      const Icon = item.icon

                      return (
                        <button
                          className="suggestion-card"
                          key={item.title}
                          onClick={() => setQuestion(item.prompt)}
                        >
                          <span className="suggestion-icon">
                            <Icon size={19} />
                          </span>
                          <span className="suggestion-title">
                            {item.title}
                          </span>
                          <span className="suggestion-description">
                            {item.description}
                          </span>
                          <span className="suggestion-arrow">
                            <ArrowRight size={16} />
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </>
              )}
            </div>
          </section>

        /* -----------------------------------------------
            HEALTH LIBRARY
        ------------------------------------------------ */

        ) : activeNav === 'Health library' ? (
          <section className="secondary-page library-page">
            <span className="eyebrow">
              <BookOpen size={15} /> YOUR SAVED HEALTH INFORMATION
            </span>

            <div className="library-heading">
              <div>
                <h1>Health library</h1>
                <p className="secondary-intro">
                  Revisit your previous questions, read saved answers, and
                  explore health information by topic.
                </p>
              </div>

              <span className="library-total">
                <FileText size={16} />
                {libraryItems.length} saved{' '}
                {libraryItems.length === 1 ? 'question' : 'questions'}
              </span>
            </div>

            {libraryError && (
              <div className="auth-error" role="alert">
                {libraryError}
              </div>
            )}

            {selectedLibraryQuestion ? (
              <div className="library-detail">
                <button
                  className="text-button library-back"
                  onClick={() => {
                    setSelectedLibraryQuestion(null)
                    setLibraryError('')
                  }}
                >
                  ← Back to library
                </button>

                <div className="library-detail-header">
                  <span className="library-topic-badge">
                    {selectedLibraryQuestion.topic || 'General Health'}
                  </span>

                  <span className="library-date">
                    <Clock3 size={14} />
                    {new Date(
                      selectedLibraryQuestion.created_at,
                    ).toLocaleString()}
                  </span>
                </div>

                <h2 className="library-question-title">
                  {selectedLibraryQuestion.question}
                </h2>

                {selectedLibraryQuestion.answer ? (
                  <>
                    <div className="library-answer">
                      <span className="section-kicker">
                        HEALTHGUIDE AI RESPONSE
                      </span>

                      <AnswerMarkdown
                        content={selectedLibraryQuestion.answer}
                      />
                    </div>

                    <div className="library-sources">
                      <div className="panel-heading">
                        <div>
                          <span className="section-kicker">
                            EVIDENCE REFERENCES
                          </span>
                          <h2>
                            Sources (
                            {selectedLibraryQuestion.sources?.length || 0})
                          </h2>
                        </div>
                        <ShieldCheck size={19} />
                      </div>

                      {selectedLibraryQuestion.sources?.length ? (
                        <ul className="library-source-list">
                          {selectedLibraryQuestion.sources.map((source) => (
                            <li key={source.id}>
                              {source.url ? (
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {source.title || 'Health information source'}
                                  <span> ↗</span>
                                </a>
                              ) : (
                                <strong>
                                  {source.title || 'Health information source'}
                                </strong>
                              )}

                              <small>
                                {source.source}
                                {source.page !== null &&
                                source.page !== undefined
                                  ? ` · Page ${source.page}`
                                  : ''}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="panel-description">
                          No source references were saved with this answer.
                        </p>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="library-old-record">
                    <FileText size={23} />
                    <strong>Answer not available</strong>
                    <p>
                      This question was saved before HealthGuide began
                      storing complete answers. Ask it again to generate a
                      new answer with its source references.
                    </p>
                    <button
                      className="primary-button"
                      onClick={() =>
                        startQuestion(selectedLibraryQuestion.question)
                      }
                    >
                      Ask again <ArrowRight size={16} />
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <div className="library-controls">
                  <div className="library-search">
                    <input
                      type="search"
                      value={librarySearch}
                      onChange={(e) => setLibrarySearch(e.target.value)}
                      placeholder="Search your saved questions..."
                      aria-label="Search saved questions"
                    />
                  </div>

                  <div className="library-filters">
                    {libraryTopics.map((topic) => (
                      <button
                        key={topic}
                        className={`library-filter ${
                          selectedTopic === topic ? 'active' : ''
                        }`}
                        onClick={() => setSelectedTopic(topic)}
                      >
                        {topic}
                      </button>
                    ))}
                  </div>
                </div>

                {libraryLoading ? (
                  <div className="library-status">
                    <Sparkles size={20} />
                    <p>Loading your saved health questions...</p>
                  </div>
                ) : libraryItems.length === 0 ? (
                  <div className="library-placeholder">
                    <div className="empty-icon">
                      <BookOpen size={25} />
                    </div>
                    <h2>Your Health Library is waiting</h2>
                    <p>
                      Questions you ask and their generated answers will
                      appear here automatically, organized by health topic.
                    </p>
                    <button
                      className="primary-button"
                      onClick={() => startQuestion()}
                    >
                      Ask your first question <ArrowRight size={16} />
                    </button>
                  </div>
                ) : filteredLibraryItems.length === 0 ? (
                  <div className="library-status">
                    <FileText size={23} />
                    <strong>No matching questions found</strong>
                    <p>
                      Try a different search term or select another topic.
                    </p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setLibrarySearch('')
                        setSelectedTopic('All topics')
                      }}
                    >
                      Clear filters
                    </button>
                  </div>
                ) : (
                  <div className="library-question-list">
                    {filteredLibraryItems.map((item) => (
                      <button
                        className="library-question-card"
                        key={item.id}
                        onClick={() => void openLibraryQuestion(item.id)}
                      >
                        <span className="library-card-icon">
                          <FileText size={19} />
                        </span>

                        <span className="library-card-content">
                          <strong>{item.question}</strong>

                          <span className="library-card-meta">
                            <span className="library-topic-badge">
                              {item.topic || 'General Health'}
                            </span>

                            <span>
                              <Clock3 size={13} />
                              {new Date(
                                item.created_at,
                              ).toLocaleDateString()}
                            </span>
                          </span>
                        </span>

                        <ArrowRight
                          className="library-card-arrow"
                          size={17}
                        />
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            {libraryDetailLoading && (
              <div className="library-loading-overlay" role="status">
                <Sparkles size={18} />
                Loading saved answer...
              </div>
            )}
          </section>

        /* -----------------------------------------------
            HOW IT WORKS
        ------------------------------------------------ */

        ) : (
          <section className="secondary-page">
            <span className="eyebrow">
              <Sparkles size={15} /> BEHIND THE ANSWERS
            </span>

            <h1>How HealthGuide works</h1>

            <p className="secondary-intro">
              The goal is to make health information easier to understand
              without hiding where it comes from or what it cannot establish.
            </p>

            <div className="process-grid">
              <article className="process-card">
                <span className="process-number">01</span>
                <BookOpen size={23} />
                <h2>Trusted sources</h2>
                <p>
                  Retrieve relevant passages from available public-health
                  documents and information providers.
                </p>
              </article>

              <article className="process-card">
                <span className="process-number">02</span>
                <ShieldCheck size={23} />
                <h2>Evidence checks</h2>
                <p>
                  Assess whether retrieved material is sufficient to support
                  an answer.
                </p>
              </article>

              <article className="process-card">
                <span className="process-number">03</span>
                <FileText size={23} />
                <h2>Traceable answers</h2>
                <p>
                  Present answers with references that point back to retrieved
                  health information.
                </p>
              </article>
            </div>

            <button
              className="primary-button"
              onClick={() => setActiveNav('Ask HealthGuide')}
            >
              Go to assistant <ArrowRight size={16} />
            </button>
          </section>
        )}

        <footer className="main-footer">
          <span>© 2026 HealthGuide AI</span>
          <button onClick={() => setShowAbout(true)}>
            About this project <ArrowRight size={13} />
          </button>
        </footer>
      </main>

      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
    </div>
  )
}

// ---------------------------------------------------------
// ABOUT MODAL
// ---------------------------------------------------------

function AboutModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="about-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="modal-close"
          aria-label="Close"
          onClick={onClose}
        >
          <X size={19} />
        </button>

        <div className="modal-icon">
          <HeartPulse size={24} />
        </div>

        <span className="eyebrow">ABOUT THE PROJECT</span>

        <h2 id="about-title">Health information deserves evidence.</h2>

        <p>
          HealthGuide AI is a capstone project exploring retrieval-augmented
          generation for public-health education. Its design includes trusted
          source retrieval, evidence sufficiency checks and traceable citations.
        </p>

        <div className="modal-info-row">
          <ShieldCheck size={18} />
          <span>It is not a diagnostic or treatment tool.</span>
        </div>

        <div className="modal-info-row">
          <Clock3 size={18} />
          <span>
            Answers are generated using available retrieved evidence. Source
            coverage and verification can vary.
          </span>
        </div>

        <button className="primary-button modal-action" onClick={onClose}>
          Got it <Check size={16} />
        </button>
      </section>
    </div>
  )
}

export default App
