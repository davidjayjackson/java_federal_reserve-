"""Test FRED_FIELDS, the metadata-field discovery helper.

FRED_FIELDS spills a two-column (field, value) array listing a series'
metadata fields -- the same field names accepted by FRED_META. With the
optional headers argument TRUE the first row is ("Field","Value").

Run against a headless LibreOffice; pass the key as argv[1].
Prints RESULT: PASS / FAIL.
"""
import sys
import time
import uno


def connect(port=2002, tries=60):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = "uno:socket,host=localhost,port=%d;urp;StarOffice.ComponentContext" % port
    last = None
    for _ in range(tries):
        try:
            return resolver.resolve(url)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise SystemExit("could not connect: %s" % last)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_fields.py <FRED_API_KEY>")
    key = sys.argv[1]

    ctx = connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, ())
    try:
        sh = doc.Sheets.getByIndex(0)
        # FRED_FIELDS spills a 2-col (field, value) array. GDP has 15 metadata
        # fields; reserve a generous range and trim empty trailing rows.
        rng = sh.getCellRangeByName("A1:B30")
        rng.setArrayFormula('=FRED_FIELDS("GDP";"%s")' % key)
        # With a header row.
        rngh = sh.getCellRangeByName("D1:E30")
        rngh.setArrayFormula('=FRED_FIELDS("GDP";"%s";TRUE())' % key)
        doc.calculateAll()
        data = [r for r in rng.getDataArray() if r[0] != ""]
        datah = [r for r in rngh.getDataArray() if r[0] != ""]
    finally:
        doc.close(False)
        desktop.terminate()

    fields = [r[0] for r in data]
    print("FRED_FIELDS('GDP') fields:", fields)
    print("first row              :", data[0] if data else None)
    print("with-headers row0      :", datah[0] if datah else None)

    # Every field FRED_FIELDS reports must be a valid FRED_META field, so the
    # canonical set should be a subset of what we got back.
    expected = {"id", "title", "units", "frequency", "seasonal_adjustment",
                "observation_start", "observation_end", "last_updated", "notes"}
    checks = {
        "has_rows": len(data) >= len(expected),
        "field_names_present": expected.issubset(set(fields)),
        "two_columns": all(len(r) == 2 for r in data),
        "values_are_text": all(isinstance(r[1], str) for r in data),
        "header_row": bool(datah) and datah[0] == ("Field", "Value"),
    }
    for name, ok in checks.items():
        print("CHECK %-22s %s" % (name, "PASS" if ok else "FAIL"))
    ok = all(checks.values())
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
