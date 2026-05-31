export const DEMO_USERS = [
  { username: 'frank',  password: 'frank123',  role: 'admin',       color: '#f26b6b', emoji: '👑' },
  { username: 'alice',  password: 'alice123',  role: 'finance',     color: '#4f9cf9', emoji: '💰' },
  { username: 'bob',    password: 'bob123',    role: 'hr',          color: '#3ecf8e', emoji: '👥' },
  { username: 'carol',  password: 'carol123',  role: 'engineering', color: '#a78bfa', emoji: '⚙️'  },
  { username: 'dave',   password: 'dave123',   role: 'legal',       color: '#f5a623', emoji: '⚖️'  },
  { username: 'eve',    password: 'eve123',    role: 'sales',       color: '#f26b6b', emoji: '📈' },
  { username: 'guest',  password: 'guest123',  role: 'viewer',      color: '#8b90a0', emoji: '👁️'  },
]

export const SOURCE_DESC = {
  finance_reports:  'P&L statements, budgets, forecasts',
  hr_records:       'Employee data, policies, payroll',
  engineering_docs: 'Architecture, APIs, runbooks',
  legal_contracts:  'MSAs, NDAs, compliance docs',
  sales_data:       'Pipeline, deals, CRM exports',
  compliance:       'GDPR, SOX, audit trails',
  operational:      'SLAs, incident reports, workflows',
  public:           'General company info',
}

export const EXAMPLE_QUERIES = {
  finance:     ['What was Q1 revenue?', 'Which department exceeded budget?', 'What is the EBITDA margin?'],
  hr:          ['How many leave days do employees get?', 'What is the performance review cycle?', 'Describe the remote work policy.'],
  engineering: ['What known issues exist in the platform?', 'What API rate limits apply?', 'How does deployment work?'],
  legal:       ['What are the payment terms in the MSA?', 'How long is data retained post-termination?', 'What governs the Nexus contract?'],
  sales:       ['Show me the top deals in Q1', 'What is the MegaCorp deal status?', 'Who owns the TechGiant opportunity?'],
  admin:       ['What was Q1 revenue?', 'How many employees are on leave?', 'What are the known platform issues?'],
  viewer:      ['What data sources are available?'],
  default:     ['What information is available?', 'Summarize the knowledge base'],
}
