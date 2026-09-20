import os

OM = 'backend/order_manager.py'

with open(OM, 'r', encoding='utf-8', newline='') as f:
    content = f.read().replace('\r\n', '\n')

print("=" * 60)
print("ORDER_MANAGER.PY KONTROL")
print("=" * 60)

checks = {
    "open_dca_position imzasi (use_limit_order)": "use_limit_order: bool = True" in content,
    "TEST MODU blogu (LIMIT)":                    "_place_entry_order_with_fallback" in content and "TEST LIMIT" in content,
    "GERCEK EMIR blogu (LIMIT)":                  "LIMIT + Fallback girisi" in content or "GERCEK EMIR" in content,
    "_place_entry_order_with_fallback METODU":    "def _place_entry_order_with_fallback" in content,
    "_save_to_db (entry_is_maker)":               "entry_is_maker=0" in content,
    "INSERT SQL (entry_is_maker)":                "entry_is_maker)" in content,
    "partial_close_position METODU":              "def partial_close_position" in content,
}

passed = 0
for k, v in checks.items():
    icon = "OK" if v else "YOK"
    print(f"  [{'X' if v else ' '}] {k:<45} {icon}")
    if v: passed += 1

print()
print(f"SONUC: {passed}/{len(checks)} kontrol gecti")
print()

if not checks["_place_entry_order_with_fallback METODU"]:
    print(">>> DUZELTME GEREKLI: _place_entry_order_with_fallback metodu eksik")
    print("    patch_fix_order_manager.py calistirilmali")
else:
    print(">>> OrderManager saglikli gorunuyor")
print("=" * 60)