#!/usr/bin/env python3
"""Prueba rápida del sistema de gestión de impuestos."""

import sys
sys.path.insert(0, '.')

try:
    from tax_payments_manager import TaxPaymentManager
    print('✓ TaxPaymentManager importado correctamente')
    
    # Probar con datos de ejemplo
    test_calcs = [
        {'id': 1, 'name': 'DICIEMBRE', 'total_amount': 1000.0, 'is_paid': True, 'created_at': '2026-01-15'},
        {'id': 2, 'name': 'NOVIEMBRE', 'total_amount': 2000.0, 'is_paid': False, 'created_at': '2026-01-20'},
        {'id': 3, 'name': 'OCTUBRE', 'total_amount': 1500.0, 'is_paid': False, 'created_at': '2025-12-10'},
    ]
    
    summary = TaxPaymentManager.calculate_payment_summary(test_calcs)
    print(f'✓ Resumen calculado:')
    print(f'  Total: RD$ {summary["total_amount"]:,.2f}')
    print(f'  Pagados: RD$ {summary["paid_amount"]:,.2f}')
    print(f'  Pendientes: RD$ {summary["pending_amount"]:,.2f}')
    print(f'  % Pagado: {summary["paid_percentage"]}%')
    print()
    
    # Probar agrupación por mes
    grouped = TaxPaymentManager.group_calculations_by_month(test_calcs)
    print(f'✓ Agrupación por mes:')
    for month, calcs in grouped.items():
        print(f'  {month}: {len(calcs)} cálculos')
    
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
