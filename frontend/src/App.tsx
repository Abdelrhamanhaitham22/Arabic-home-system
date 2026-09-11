import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import './App.css'

type Language = 'ar' | 'ru'
type Result = {
  exam_name: string
  score: number
  max_score: number
  percentage: number
  exam_date: string
}
type ResultResponse = { student_name: string; student_code: string; results: Result[]; message?: string }

type ApiObject = Record<string, unknown>
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

function csrfToken() {
  return document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='))?.split('=')[1] || ''
}

async function readResponse(response: Response): Promise<ApiObject> {
  const text = await response.text()
  if (!text) throw new Error('The server did not return a response. Start the backend and try again.')
  try { return JSON.parse(text) as Record<string, unknown> } catch { throw new Error('The server returned an invalid response. Check that the backend is running.') }
}

function isResultResponse(body: ApiObject): body is ResultResponse {
  return typeof body.student_name === 'string' && typeof body.student_code === 'string' && Array.isArray(body.results)
}

const copy = {
  ar: {
    home: 'الرئيسية', register: 'تسجيل طالب', results: 'النتائج', teacher: 'للمعلمين', arabic: 'العربية', russian: 'Русский',
    eyebrow: 'بوابتك إلى التعلّم', hero: 'نتيجتك.\nخطوتك التالية.', heroBody: 'سجّل بياناتك مرة واحدة، واحتفظ برمزك الدائم للوصول إلى نتائج اختباراتك في أي وقت.',
    start: 'تسجيل طالب', check: 'تحقق من نتيجتك', trust: 'خدمة بسيطة، واضحة، ومصممة لتكون معك في كل خطوة.', resultsBody: 'أدخل رمزك الطلابي لرؤية نتائج الاختبارات المنشورة ومتابعة تقدمك.',
    registerTitle: 'أنشئ ملفك الطلابي', registerBody: 'أدخل بياناتك كما تظهر في وثائقك. سنرسل لك رمزاً دائماً بعد التسجيل.',
    fullName: 'الاسم الكامل', phone: 'رقم الهاتف', address: 'العنوان', passport: 'رقم جواز السفر', language: 'لغة العرض المفضلة', choose: 'اختر اللغة', submit: 'إتمام التسجيل', registering: 'جارٍ التسجيل…',
    yourCode: 'رمزك الطلابي الدائم', saveCode: 'احتفظ بهذا الرمز. ستحتاج إليه كلما أردت التحقق من نتائجك.', copy: 'نسخ الرمز', copied: 'تم النسخ', registerAnother: 'تسجيل طالب آخر',
    resultsTitle: 'اعرف نتيجتك', code: 'الرمز الطلابي', codeHint: 'مثال: ST202600001', search: 'عرض النتيجة', searching: 'جارٍ البحث…',
    student: 'الطالب', published: 'نتائج منشورة', noResults: 'لم تُنشر نتيجة بعد', noResultsBody: 'ستظهر نتائجك هنا فور اعتمادها. احتفظ برمزك وحاول مرة أخرى لاحقاً.', exam: 'الاختبار', score: 'الدرجة', date: 'التاريخ', percentage: 'النسبة', notFound: 'لم نعثر على هذا الرمز', notFoundBody: 'تحقق من الرمز المكتوب. يجب أن يبدأ بـ ST ويتبعه العام والرقم التسلسلي.',
    required: 'يرجى إكمال هذا الحقل.', footer: 'نتعلم اليوم لنفتح أبواب الغد.',
  },
  ru: {
    home: 'Главная', register: 'Добавить студента', results: 'Результаты', teacher: 'Для учителей', arabic: 'العربية', russian: 'Русский',
    eyebrow: 'Ваш путь к обучению', hero: 'Ваш результат.\nВаш следующий шаг.', heroBody: 'Зарегистрируйтесь один раз и сохраните постоянный код для доступа к результатам экзаменов в любое время.',
    start: 'Добавить студента', check: 'Проверить результат', trust: 'Простой и понятный сервис, который сопровождает вас на каждом шаге.', resultsBody: 'Введите код студента, чтобы увидеть опубликованные результаты и следить за прогрессом.',
    registerTitle: 'Создайте профиль студента', registerBody: 'Введите данные так, как они указаны в ваших документах. После регистрации вы получите постоянный код.',
    fullName: 'Полное имя', phone: 'Номер телефона', address: 'Адрес', passport: 'Номер паспорта', language: 'Язык интерфейса', choose: 'Выберите язык', submit: 'Завершить регистрацию', registering: 'Регистрация…',
    yourCode: 'Ваш постоянный код', saveCode: 'Сохраните этот код. Он понадобится для проверки результатов.', copy: 'Скопировать код', copied: 'Скопировано', registerAnother: 'Зарегистрировать ещё',
    resultsTitle: 'Проверьте результат', code: 'Код студента', codeHint: 'Например: ST202600001', search: 'Показать результат', searching: 'Поиск…',
    student: 'Студент', published: 'Опубликованные результаты', noResults: 'Результатов пока нет', noResultsBody: 'Результат появится здесь после публикации. Сохраните код и попробуйте позже.', exam: 'Экзамен', score: 'Баллы', date: 'Дата', percentage: 'Процент', notFound: 'Код не найден', notFoundBody: 'Проверьте код. Он должен начинаться с ST, затем идут год и порядковый номер.',
    required: 'Заполните это поле.', footer: 'Учимся сегодня, открываем возможности завтра.',
  },
} as const

function App() {
  const [language, setLanguage] = useState<Language>(() => (localStorage.getItem('language') as Language) || 'ar')
  const t = copy[language]
  useEffect(() => { localStorage.setItem('language', language); document.documentElement.lang = language; document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr' }, [language])
  return <BrowserRouter><div className="app-shell"><Header language={language} setLanguage={setLanguage} t={t} /><main><Routes><Route path="/" element={<Home t={t} />} /><Route path="/teacher" element={<TeacherLogin t={t} />} /><Route path="/teacher/students/new" element={<TeacherStudentEntry t={t} />} /><Route path="/results" element={<Results t={t} />} /></Routes></main><Footer t={t} /></div></BrowserRouter>
}

type Copy = (typeof copy)[Language]

function Header({ language, setLanguage, t }: { language: Language; setLanguage: (language: Language) => void; t: Copy }) {
  const location = useLocation()
  return <header className="site-header"><Link className="brand" to="/"><span className="brand-mark">أ</span><span><strong>مدار</strong><small>student portal</small></span></Link><nav aria-label="Main navigation"><Link className={location.pathname === '/' ? 'active' : ''} to="/">{t.home}</Link><Link className={location.pathname === '/teacher' ? 'active' : ''} to="/teacher">{t.teacher}</Link><Link className={location.pathname === '/results' ? 'active' : ''} to="/results">{t.results}</Link></nav><div className="language-switcher" aria-label="Language switcher"><button className={language === 'ar' ? 'selected' : ''} onClick={() => setLanguage('ar')}>{t.arabic}</button><span>/</span><button className={language === 'ru' ? 'selected' : ''} onClick={() => setLanguage('ru')}>{t.russian}</button></div></header>
}

function Home({ t }: { t: Copy }) {
  return <div className="page home-page"><section className="hero-section"><div className="hero-copy"><p className="eyebrow"><span className="eyebrow-dot" />{t.eyebrow}</p><h1>{t.hero.split('\n').map((line, index) => <span key={line} className={index ? 'accent-line' : ''}>{line}<br /></span>)}</h1><p className="hero-body">{t.heroBody}</p><div className="hero-actions"><Link className="button primary" to="/teacher">{t.start}<span>↗</span></Link><Link className="button text-button" to="/results">{t.check}<span>→</span></Link></div></div><div className="hero-visual" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><div className="visual-core"><span>أ</span><small>مدار</small></div><div className="visual-note note-top">01 <span>learn</span></div><div className="visual-note note-bottom">result <span>→</span></div></div></section><section className="trust-line"><span className="line" /><p>{t.trust}</p><span className="line" /></section><section className="home-paths"><div className="path-lead"><span className="path-index">01</span><h2>{t.register}</h2><p>{t.registerBody}</p><Link to="/teacher" className="arrow-link">{t.start} <span>↗</span></Link></div><div className="path-lead secondary"><span className="path-index">02</span><h2>{t.results}</h2><p>{t.resultsBody}</p><Link to="/results" className="arrow-link">{t.check} <span>↗</span></Link></div></section></div>
}

function TeacherLogin({ t }: { t: Copy }) {
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    await fetch(`${apiBaseUrl}/students/csrf/`, { credentials: 'include' })
    const response = await fetch(`${apiBaseUrl}/students/login/`, { method: 'POST', credentials: 'include', headers: { 'X-CSRFToken': csrfToken(), 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ username: String(form.get('username') || ''), password: String(form.get('password') || '') }) })
    if (response.ok) window.location.href = '/teacher/students/new'
    else setError(t.teacher)
  }
  return <div className="page centered-page"><div className="form-heading"><p className="eyebrow">{t.teacher}</p><h1>{t.teacher}</h1></div><form className="student-form" onSubmit={submit}><label className="field"><span>Username</span><input name="username" required /></label><label className="field"><span>Password</span><input name="password" type="password" required /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button primary submit-button">{t.teacher}</button></form></div>
}

function TeacherStudentEntry({ t }: { t: Copy }) {
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  useEffect(() => { fetch(`${apiBaseUrl}/students/session/`, { credentials: 'include' }).then(response => setAuthorized(response.ok)).catch(() => setAuthorized(false)) }, [])
  if (authorized === null) return <div className="page centered-page"><p>{t.registering}</p></div>
  if (!authorized) return <Navigate to="/teacher" replace />
  return <Register t={t} />
}

function Register({ t }: { t: Copy }) {
  const [form, setForm] = useState({ full_name: '', phone_number: '', address: '', passport_number: '', preferred_language: 'ar' })
  const [state, setState] = useState<{ loading: boolean; error: string; code: string }>({ loading: false, error: '', code: '' })
  const update = (field: keyof typeof form, value: string) => setForm({ ...form, [field]: value })
  async function submit(event: FormEvent) { event.preventDefault(); setState({ loading: true, error: '', code: '' }); try { await fetch(`${apiBaseUrl}/students/csrf/`, { credentials: 'include' }); const response = await fetch(`${apiBaseUrl}/students/register/`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(form) }); const body = await readResponse(response); if (!response.ok) { const details = Object.values(body).flat().map(String).join(' '); throw new Error(details || 'Request failed') } if (typeof body.student_code !== 'string') throw new Error('The server returned an invalid registration response.'); setState({ loading: false, error: '', code: body.student_code }) } catch (error) { setState({ loading: false, error: error instanceof Error ? error.message : 'Request failed', code: '' }) } }
  if (state.code) return <div className="page centered-page"><div className="success-symbol">✓</div><p className="eyebrow">{t.register}</p><h1>{t.yourCode}</h1><div className="code-display">{state.code}</div><p className="form-intro">{t.saveCode}</p><div className="success-actions"><button className="button primary" onClick={() => navigator.clipboard?.writeText(state.code)}>{t.copy}<span>↗</span></button><button className="button text-button" onClick={() => setState({ loading: false, error: '', code: '' })}>{t.registerAnother}</button></div></div>
  return <div className="page form-page"><div className="form-heading"><p className="eyebrow"><span className="eyebrow-dot" />{t.register}</p><h1>{t.registerTitle}</h1><p className="form-intro">{t.registerBody}</p></div><form className="student-form" onSubmit={submit}><Field label={t.fullName} value={form.full_name} onChange={value => update('full_name', value)} required /><Field label={t.phone} value={form.phone_number} onChange={value => update('phone_number', value)} type="tel" required /><Field label={t.address} value={form.address} onChange={value => update('address', value)} required /><Field label={t.passport} value={form.passport_number} onChange={value => update('passport_number', value)} required /><label className="field"><span>{t.language}</span><select value={form.preferred_language} onChange={event => update('preferred_language', event.target.value)}><option value="ar">{t.arabic}</option><option value="ru">{t.russian}</option></select></label>{state.error && <p className="form-error" role="alert">{state.error}</p>}<button className="button primary submit-button" disabled={state.loading}>{state.loading ? t.registering : t.submit}<span>↗</span></button></form></div>
}

function Field({ label, value, onChange, type = 'text', required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) { return <label className="field"><span>{label}{required && <b aria-hidden="true">*</b>}</span><input type={type} value={value} onChange={event => onChange(event.target.value)} required={required} /></label> }

function Results({ t }: { t: Copy }) {
  const [code, setCode] = useState(''); const [state, setState] = useState<{ loading: boolean; error: string; response: ResultResponse | null }>({ loading: false, error: '', response: null })
  async function search(event: FormEvent) { event.preventDefault(); setState({ loading: true, error: '', response: null }); try { const response = await fetch(`${apiBaseUrl}/results/${code.trim().toUpperCase()}/`); const body = await readResponse(response); if (!response.ok) throw new Error(String(body.message || t.notFound)); if (!isResultResponse(body)) throw new Error('The server returned an invalid results response.'); setState({ loading: false, error: '', response: body }) } catch (error) { setState({ loading: false, error: error instanceof Error ? error.message : t.notFound, response: null }) } }
  return <div className="page results-page"><div className="results-heading"><p className="eyebrow"><span className="eyebrow-dot" />{t.results}</p><h1>{t.resultsTitle}</h1><p className="form-intro">{t.resultsBody}</p></div><form className="lookup-form" onSubmit={search}><label className="field"><span>{t.code}</span><input value={code} onChange={event => setCode(event.target.value)} placeholder={t.codeHint} required /></label><button className="button primary" disabled={state.loading}>{state.loading ? t.searching : t.search}<span>→</span></button></form>{state.error && <div className="notice error-notice" role="alert"><strong>{t.notFound}</strong><p>{state.error || t.notFoundBody}</p></div>}{state.response && <ResultPanel response={state.response} t={t} />}</div>
}

function ResultPanel({ response, t }: { response: ResultResponse; t: Copy }) { return <section className="result-panel" aria-live="polite"><div className="result-head"><div><p className="result-label">{t.student}</p><h2>{response.student_name}</h2></div><span className="code-pill">{response.student_code}</span></div>{response.results.length ? <><p className="result-section-title">{t.published}</p><div className="result-list">{response.results.map(result => <article className="result-row" key={`${result.exam_name}-${result.exam_date}`}><div><h3>{result.exam_name}</h3><p>{result.exam_date}</p></div><div className="score"><strong>{result.score}<small> / {result.max_score}</small></strong><span>{result.percentage}%</span></div></article>)}</div></> : <div className="empty-result"><strong>{t.noResults}</strong><p>{response.message || t.noResultsBody}</p></div>}</section> }

function Footer({ t }: { t: Copy }) { return <footer><span>مدار / 2026</span><p>{t.footer}</p><span>AR · RU</span></footer> }

export default App
