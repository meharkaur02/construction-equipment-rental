export const mockMachines = [
  {
    id: 1,
    machine_code: "CAT-EX-001",
    name: "CAT 320 Excavator",
    equipment_type: "Excavator",
    district: "District 1",
    status: "AVAILABLE",
  },
  {
    id: 2,
    machine_code: "CAT-EX-002",
    name: "CAT 320 Excavator",
    equipment_type: "Excavator",
    district: "District 2",
    status: "AVAILABLE",
  },
  {
    id: 3,
    machine_code: "LIEB-CR-001",
    name: "Liebherr Mobile Crane",
    equipment_type: "Crane",
    district: "District 1",
    status: "AVAILABLE",
  },
  {
    id: 4,
    machine_code: "PUMP-001",
    name: "Putzmeister Concrete Pump",
    equipment_type: "Concrete Pump",
    district: "District 3",
    status: "AVAILABLE",
  },
];

/*
 * These are the billing plans displayed to the customer
 * before a contract is created.
 *
 * The actual contract is created through:
 * POST /contracts
 *
 * and the final invoice is calculated by the backend.
 */
export const billingPlans = [
  {
    type: "HOURLY",
    name: "Hourly",
    description: "Flexible billing based on machine usage",
    rate: 1500,
    unit: "hour",
    minimumHours: 8,
    minimumText: "8 hour daily minimum",
  },
  {
    type: "DAILY",
    name: "Daily",
    description: "Simple daily rental pricing",
    rate: 10000,
    unit: "day",
    minimumText: "Charged per rental day",
  },
  {
    type: "MONTHLY",
    name: "Monthly",
    description: "Designed for long-term projects",
    rate: 200000,
    unit: "month",
    hourCap: 200,
    overageRate: 1000,
    minimumText: "200 hour cap • ₹1,000/hour overage",
  },
];

/*
 * These are retained only for reference/demo purposes.
 * Billing displayed in the application should come from
 * GET /billing/invoices.
 */
export const mockInvoices = [];

export const mockBookings = [];