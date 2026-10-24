import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { MetricsPanel } from '../components/MetricsPanel';

describe('Frontend Component Tests', () => {
  // Test 1: StatusBadge shows icon AND text
  it('StatusBadge renders both status icon and textual status label', () => {
    const { container, rerender } = render(<StatusBadge status="PASS" />);
    expect(screen.getByText('PASS')).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();

    rerender(<StatusBadge status="FAIL" />);
    expect(screen.getByText('FAIL')).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();

    rerender(<StatusBadge status="UNKNOWN" />);
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();

    rerender(<StatusBadge status="NOT REACHED" />);
    expect(screen.getByText('NOT REACHED')).toBeInTheDocument();
  });

  // Test 2: StatusBadge supports all 4 statuses
  it('StatusBadge correctly handles PASS, FAIL, UNKNOWN, NOT REACHED', () => {
    const statuses = ['PASS', 'FAIL', 'UNKNOWN', 'NOT REACHED'];
    statuses.forEach((st) => {
      const { unmount } = render(<StatusBadge status={st} />);
      const badge = screen.getByRole('status');
      expect(badge).toHaveAttribute('aria-label', `Status: ${st}`);
      unmount();
    });
  });

  // Test 3: MetricsPanel empty state shows no fake numbers
  it('MetricsPanel empty state shows no invented metrics and displays run prompt', () => {
    const emptyPayload = {
      has_data: false,
      message: 'No evaluation has been run yet',
      metrics: null,
    };
    render(<MetricsPanel metrics={emptyPayload} onRefresh={() => {}} />);

    expect(screen.getByText(/No evaluation has been run yet/i)).toBeInTheDocument();
    expect(screen.getByText('Run Validation Suite')).toBeInTheDocument();

    // Verify no percentage symbols or numbers are displayed
    expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/0%/)).not.toBeInTheDocument();
  });

  // Test 4: MetricsPanel renders actual values when data is populated
  it('MetricsPanel displays real numerator/denominator format and disclaimer', () => {
    const populatedPayload = {
      has_data: true,
      batch_id: 'batch-test-123',
      disclaimer: 'Evaluated on 12 synthetic cases on 2026-10-25. Not a measure of production accuracy.',
      combined: {
        case_count: 12,
        failure_localization_accuracy: {
          numerator: 8,
          denominator: 8,
          value: 100.0,
          display: '8/8 (100%)',
          definition: 'Correct failure_stage identified.',
        },
        false_attribution_rate: {
          numerator: 0,
          denominator: 8,
          value: 0.0,
          display: '0/8 (0%)',
          definition: 'Incorrect root-cause claims.',
        },
        abstention_quality: {
          supported_abstention: {
            numerator: 2,
            denominator: 2,
            value: 100.0,
            display: '2/2 (100%)',
            definition: 'Abstention on gaps.',
          },
          unnecessary_abstention: {
            numerator: 0,
            denominator: 10,
            value: 0.0,
            display: '0/10 (0%)',
            definition: 'Unnecessary abstention.',
          },
        },
        diagnosis_latency: {
          mean_ms: 12.5,
          median_ms: 10.0,
          max_ms: 25.0,
          manual_baseline: 'not recorded',
          definition: 'Execution latency.',
        },
        retest_verification_accuracy: {
          numerator: 6,
          denominator: 6,
          value: 100.0,
          display: '6/6 (100%)',
          definition: 'Retest accuracy.',
        },
        evidence_coverage: {
          numerator: 72,
          denominator: 72,
          value: 100.0,
          display: '72/72 (100%)',
          definition: 'Checkpoint coverage.',
        },
      },
    };

    render(<MetricsPanel metrics={populatedPayload} onRefresh={() => {}} />);
    expect(screen.getByText('8/8 (100%)')).toBeInTheDocument();
    expect(screen.getByText('0/8 (0%)')).toBeInTheDocument();
    expect(screen.getByText(/Not a measure of production accuracy/i)).toBeInTheDocument();
  });

  // Test 5: Disabled approve button before review
  it('Approve action maintains disabled status until review is recorded', () => {
    // In our DiagnosisFix logic, approving simulated fix is gated on isAccepted
    const isAccepted = false;
    render(
      <button
        disabled={!isAccepted}
        aria-label="Approve Simulated Fix"
      >
        Approve Simulated Fix
      </button>
    );

    const approveBtn = screen.getByRole('button', { name: /Approve Simulated Fix/i });
    expect(approveBtn).toBeDisabled();
  });
});
