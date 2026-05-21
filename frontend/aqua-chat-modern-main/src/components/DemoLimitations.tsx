import { AlertTriangle, Database, MessageSquare, CreditCard, Smartphone, Settings } from "lucide-react";

export default function DemoLimitations() {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-amber-900 mb-3">🚧 Demo System</h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Database className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-amber-900">Sample Data</div>
                <div className="text-xs text-amber-700">Uses a local SQLite database with three demo LgWSC accounts (000001, 000002, 000003) for demonstration purposes.</div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <MessageSquare className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-amber-900">Groq AI Integration</div>
                <div className="text-xs text-amber-700">Natural language understanding powered by Groq AI (Llama 3.1). Falls back to deterministic responses when offline.</div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <CreditCard className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-amber-900">No Real Payments</div>
                <div className="text-xs text-amber-700">Payment processing is simulated. Real deployment would integrate with MTN Mobile Money, Airtel Money, ZANACO, and other LgWSC payment channels.</div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Smartphone className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-amber-900">Web Interface Only</div>
                <div className="text-xs text-amber-700">WhatsApp Business API integration is not yet active. This web UI demonstrates the full conversation flow.</div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Settings className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-amber-900">Production-Ready Architecture</div>
                <div className="text-xs text-amber-700">Designed to connect to LgWSC's live billing, CRM, and outage management systems with minimal changes.</div>
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-3 border-t border-amber-200">
            <div className="text-xs text-amber-800 font-medium">
              This is a capstone research prototype for Lukanga Water Supply and Sanitation Company (LgWSC), Central Province, Zambia.
              Demo PINs: account 000001 → 1234 | 000002 → 5678 | 000003 → 9012.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
