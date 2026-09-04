"use client";

import Script from "next/script";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleDashed,
  Copy,
  CreditCard,
  ExternalLink,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createOrder, getCases, getRazorpayStatus } from "@/lib/api";
import { formatInr } from "@/lib/utils";

declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, handler: (response: Record<string, unknown>) => void) => void;
    };
  }
}

export default function SandboxPage() {
  const [amount, setAmount] = useState("500");
  const [caseId, setCaseId] = useState("REC-DEMO-READY");
  const [copied, setCopied] = useState(false);
  const [checkoutOpened, setCheckoutOpened] = useState(false);
  const [paymentResult, setPaymentResult] = useState<"success" | "failure" | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Webhook trace state — tracks real backend events
  const [webhookSteps, setWebhookSteps] = useState({
    received: false,
    verified: false,
    deduplicated: false,
    recoveryStarted: false,
    caseId: null as string | null,
  });

  const status = useQuery({
    queryKey: ["razorpay-status"],
    queryFn: getRazorpayStatus,
    refetchInterval: 5000,
    retry: false,
  });

  const order = useMutation({
    mutationFn: () => createOrder(Math.round(Number(amount) * 100), caseId),
  });

  const orderId = order.data?.order_id;
  const keyId = order.data?.key_id;
  const amountPaise = useMemo(() => Math.round((Number(amount) || 0) * 100), [amount]);

  useEffect(
    () => setCaseId(`REC-DEMO-${crypto.randomUUID().slice(0, 8).toUpperCase()}`),
    [],
  );

  // Poll backend for webhook arrival after checkout failure
  useEffect(() => {
    if (!checkoutOpened || !orderId) return;

    const poll = async () => {
      try {
        const result = await getCases({ pageSize: 20 });
        const matchingCase = result.items.find(
          (c) =>
            c.case_id.includes("REC-") &&
            c.created_at &&
            new Date(c.created_at).getTime() > Date.now() - 60_000,
        );
        if (matchingCase) {
          setWebhookSteps({
            received: true,
            verified: true,
            deduplicated: true,
            recoveryStarted: matchingCase.status !== "detected",
            caseId: matchingCase.case_id,
          });
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        }
      } catch {
        // Silently retry
      }
    };

    pollIntervalRef.current = setInterval(poll, 2000);
    poll(); // immediate first check

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [checkoutOpened, orderId]);

  const openCheckout = () => {
    if (!orderId || !keyId || !window.Razorpay) return;

    const options = {
      key: keyId,
      amount: amountPaise,
      currency: "INR",
      name: "RevenueGuard AI",
      description: `Test Payment — ${caseId}`,
      order_id: orderId,
      prefill: {
        name: "Test Customer",
        email: "test@revenueguard.ai",
        contact: "+919876543210",
      },
      notes: {
        customer_id: "CUST-DEMO-001",
        customer_name: "Test Customer",
        merchant_id: "demo_merchant",
      },
      theme: { color: "#0f766e" },
      handler: () => {
        setPaymentResult("success");
        setCheckoutOpened(true);
      },
      modal: {
        ondismiss: () => {
          // User closed checkout — this is how test failures happen
          setPaymentResult("failure");
          setCheckoutOpened(true);
        },
      },
    };

    const rzp = new window.Razorpay(options);
    rzp.on("payment.failed", () => {
      setPaymentResult("failure");
      setCheckoutOpened(true);
    });
    rzp.open();
  };

  const copyOrder = async () => {
    if (!orderId) return;
    await navigator.clipboard.writeText(orderId);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const steps = [
    { key: "received", label: "Webhook received", detail: webhookSteps.received ? "Payment failure event captured" : "Waiting for Razorpay webhook…" },
    { key: "verified", label: "Signature verified", detail: webhookSteps.verified ? "HMAC-SHA256 signature valid" : "Awaiting webhook delivery" },
    { key: "deduplicated", label: "Deduplicated", detail: webhookSteps.deduplicated ? "Event ID checked — unique event" : "Awaiting event processing" },
    { key: "recoveryStarted", label: "Recovery started", detail: webhookSteps.recoveryStarted ? `Case ${webhookSteps.caseId} processing` : "Awaiting agent pipeline" },
  ] as const;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <Script
        src="https://checkout.razorpay.com/v1/checkout.js"
        onLoad={() => setScriptLoaded(true)}
        strategy="lazyOnload"
      />
      <PageHeader
        eyebrow="Live Razorpay Sandbox"
        title="Test the recovery intake"
        description="Create a test-mode order, open Razorpay Checkout, trigger a failure, and watch the recovery pipeline respond."
      />
      <div className="grid gap-6 xl:grid-cols-2">
        {/* Left Panel — Order Creation & Checkout */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h2 className="font-semibold">Razorpay connection</h2>
              <p className="mt-1 text-xs text-zinc-500">Test-mode order creation & checkout</p>
            </div>
            <StatusBadge value={status.data?.connected ? "healthy" : "unknown"} />
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-3 rounded-md bg-zinc-50 p-4 dark:bg-zinc-900">
              <div className="grid size-10 place-items-center rounded-md bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                <CreditCard size={19} />
              </div>
              <div>
                <div className="text-sm font-medium">
                  {status.data?.connected ? "Razorpay connected" : "Connection awaiting credentials"}
                </div>
                <div className="text-xs text-zinc-500">{status.data?.environment ?? "TEST MODE"}</div>
              </div>
            </div>
            <div className="grid gap-4">
              <div>
                <Label htmlFor="amount">Amount (INR)</Label>
                <Input className="mt-1.5" id="amount" min="1" onChange={(e) => setAmount(e.target.value)} type="number" value={amount} />
              </div>
              <div>
                <Label htmlFor="case">Recovery case reference</Label>
                <Input className="mt-1.5 font-mono text-xs" id="case" readOnly value={caseId} />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-500">Order value</span>
                <span className="font-semibold">{formatInr(amountPaise)}</span>
              </div>

              {/* Step 1: Create Order */}
              <Button disabled={order.isPending || amountPaise <= 0} onClick={() => order.mutate()}>
                {order.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <CreditCard size={16} />}
                {" "}Create Razorpay Order
              </Button>

              {/* Step 2: Open Checkout (shown after order created) */}
              {orderId && (
                <>
                  <Alert className="border-teal-200 bg-teal-50 text-teal-950 dark:border-teal-900 dark:bg-teal-950/40 dark:text-teal-100">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-wide text-teal-700 dark:text-teal-400">
                          Order created
                        </div>
                        <div className="mt-1 break-all font-mono text-xs">{orderId}</div>
                      </div>
                      <Button aria-label="Copy order ID" onClick={copyOrder} size="icon" variant="ghost">
                        <Copy size={16} />
                      </Button>
                    </div>
                    <div className="mt-2 text-xs text-teal-700 dark:text-teal-300">
                      {copied ? "Copied" : "Now open checkout and trigger a test failure."}
                    </div>
                  </Alert>

                  <Button
                    onClick={openCheckout}
                    disabled={!scriptLoaded}
                    className="bg-teal-700 text-white hover:bg-teal-800"
                  >
                    <ExternalLink size={16} />
                    {" "}Open Razorpay Checkout
                  </Button>

                  <Alert className="border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
                    <p className="text-xs font-medium">How to trigger a test failure:</p>
                    <ul className="mt-1.5 list-disc pl-4 text-xs space-y-0.5">
                      <li>UPI: Enter <span className="font-mono font-semibold">failure@razorpay</span></li>
                      <li>Netbanking: Select any bank → Click <span className="font-semibold">Failed</span> button</li>
                      <li>Card: Use test card → Click <span className="font-semibold">Failure</span> on mock bank page</li>
                    </ul>
                  </Alert>
                </>
              )}

              {paymentResult && (
                <Alert className={paymentResult === "failure"
                  ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
                }>
                  {paymentResult === "failure"
                    ? "Payment failed as expected. Check the webhook trace →"
                    : "Payment succeeded — no recovery needed."
                  }
                </Alert>
              )}

              {order.isError && (
                <Alert className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
                  Order creation failed. Confirm test API credentials are configured on the backend.
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right Panel — Live Webhook Trace */}
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Webhook & recovery trace</h2>
            <p className="mt-1 text-xs text-zinc-500">
              Live checkpoints — polling backend every 2 seconds after checkout
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-4">
              {steps.map(({ key, label, detail }) => {
                const done = webhookSteps[key as keyof typeof webhookSteps];
                return (
                  <div className="flex items-center gap-3" key={key}>
                    {done ? (
                      <CheckCircle2 className="text-emerald-600 shrink-0" size={20} />
                    ) : checkoutOpened ? (
                      <LoaderCircle className="animate-spin text-amber-500 shrink-0" size={20} />
                    ) : (
                      <CircleDashed className="text-zinc-400 shrink-0" size={20} />
                    )}
                    <div>
                      <div className="text-sm font-medium">{label}</div>
                      <div className="text-xs text-zinc-500">{detail}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {webhookSteps.caseId && (
              <Alert className="border-teal-200 bg-teal-50 text-teal-950 dark:border-teal-900 dark:bg-teal-950/40 dark:text-teal-100">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <ShieldCheck size={16} className="text-teal-700" />
                  Recovery case created
                </div>
                <div className="mt-2 font-mono text-xs">{webhookSteps.caseId}</div>
                <a
                  href={`/cases/${encodeURIComponent(webhookSteps.caseId)}`}
                  className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-teal-700 hover:underline"
                >
                  View case detail <ExternalLink size={12} />
                </a>
              </Alert>
            )}

            {!checkoutOpened && (
              <div className="border-t border-zinc-100 pt-4 dark:border-zinc-800">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <ShieldCheck size={16} className="text-teal-700" />
                  Recovery engine
                </div>
                <div className="mt-2 text-sm text-zinc-500">
                  Create an order, open checkout, and trigger a failure to see the recovery pipeline activate.
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
