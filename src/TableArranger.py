# TODO: Refactor to link this with JsonLoader / Editor etc.

def arrangeTable(
        table, fontSize = 18,
        getHeight = lambda t, r : t.item(r, 1).text().count("\n") + 1,
        calcHeight = lambda fontSize, lines: 20 + (15 + fontSize) * lines):

    for row in range(table.rowCount()):
        arrangeRow(table, row, fontSize, getHeight, calcHeight)

def arrangeRow(
        table, row, fontSize = 18,
        getHeight = lambda t, r : t.item(r, 1).text().count("\n") + 1,
        calcHeight = lambda fontSize, lines: 20 + (15 + fontSize) * lines):

    table.setRowHeight(row, calcHeight(fontSize, getHeight(table, row)))