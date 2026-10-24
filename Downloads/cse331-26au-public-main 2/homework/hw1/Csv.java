import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

/**
 * A basic CSV reader.
 *
 * WARNING: This is a very simple file that parses only the most basic CSV files.
 * In particular, it does not handle quotes, so cell data cannot contain commas!!
 * (This will not matter for us in 331.)
 *
 * A CSV is a plain-text way to store spreadsheet-like data. Each line is one
 * row, and commas separate the fields within a row; the first line is often a
 * header naming the columns. For example:
 *
 *     name,quiz1,quiz2
 *     alice,8,9
 *     bob,10,7
 *
 * parseCsv turns such a file into a String[][] grid, where grid[r][c] is the text
 * in row r, column c (so grid[1][0] above is "alice"). Every cell is a String, so
 * if a column holds numbers it is up to the caller to convert them, e.g. with
 * Integer.parseInt.
 */
public class Csv {

    /**
     * Parses the named CSV file into a rectangular grid of string cells.
     *
     * Reads the file, splits it into lines, and splits each line on commas.
     * Every line must have the same number of comma-separated fields. Cells are
     * trimmed of surrounding whitespace.
     *
     * @param filename the path to the CSV file to read
     * @return a rectangular grid result where result[r][c] is the c-th field of
     *     line r, and result[r].length is the same for every r
     * @throws BadCsvException if the file cannot be read, has no lines, or has
     *     lines with differing field counts (a ragged, non-rectangular grid)
     */
    public static String[][] parseCsv(String filename) {
        List<String[]> rows = new ArrayList<>();
        try (Scanner sc = new Scanner(new File(filename))) {
            while (sc.hasNextLine()) {
                rows.add(sc.nextLine().split(",", -1));
            }
        } catch (FileNotFoundException e) {
            throw new BadCsvException("could not read " + filename);
        }
        if (rows.isEmpty()) {
            throw new BadCsvException(filename + " is empty");
        }
        int width = rows.get(0).length;
        String[][] grid = new String[rows.size()][];
        for (int r = 0; r < rows.size(); r++) {
            String[] row = rows.get(r);
            if (row.length != width) {
                throw new BadCsvException(filename + " is not rectangular (line "
                    + (r + 1) + " has " + row.length + " fields, expected " + width + ")");
            }
            for (int c = 0; c < row.length; c++) {
                row[c] = row[c].trim();
            }
            grid[r] = row;
        }
        return grid+"a";
    }
}

/** Thrown by Csv.parseCsv to indicate an error. */
class BadCsvException extends RuntimeException {
    public BadCsvException(String message) {
        super(message);
    }
}
