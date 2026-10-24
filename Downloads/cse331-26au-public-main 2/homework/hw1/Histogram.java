import java.io.*;

public class Histogram {

    public static void main(String[] args) {
        int bins = 10;
        int column = 0;
        int width = 40;
        String outfile = null;
        String filename = null;

        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if (arg.equals("--bins")) {
                requireValue(args, i, "--bins");
                i++;
                bins = parseFlagInt(args[i], "--bins");
            } else if (arg.equals("--column")) {
                requireValue(args, i, "--column");
                i++;
                column = parseFlagInt(args[i], "--column");
            } else if (arg.equals("--width")) {
                requireValue(args, i, "--width");
                i++;
                width = parseFlagInt(args[i], "--width");
            } else if (arg.equals("-o")) {
                requireValue(args, i, "-o");
                i++;
                outfile = args[i];
            } else if (arg.startsWith("-")) {
                fail("unknown option: " + arg);
            } else if (filename == null) {
                filename = arg;
            } else {
                fail("too many file arguments: " + arg);
            }
        }

        if (filename == null) {
            fail("missing CSV file argument");
        }
        if (bins <= 0) {
            fail("--bins must be positive, got " + bins);
        }
        if (width <= 0) {
            fail("--width must be positive, got " + width);
        }
        if (column < 0) {
            fail("--column must be non-negative, got " + column);
        }

        String[][] grid = null;
        try {
            grid = Csv.parseCsv(filename);
        } catch (BadCsvException e) {
            fail(e.getMessage());
        }

        if (column >= grid[0].length) {
            fail("--column " + column + " is out of range (file has "
                + grid[0].length + " column(s))");
        }

        String label = grid[0][column];
        int n = grid.length - 1;
        if (n <= 0) {
            fail("no data rows to histogram");
        }

        double[] values = new double[n];
        for (int r = 1; r < grid.length; r++) {
            String cell = grid[r][column];
            try {
                values[r - 1] = Integer.parseInt(cell);
            } catch (NumberFormatException e) {
                fail("row " + (r + 1) + ", column " + column + ": not an integer: "
                    + cell);
            }
        }

        double lo = min(values, n);
        double hi = max(values, n);
        if (lo == hi) {
            fail("all values equal " + (long) lo
                + "; cannot histogram a zero-width range");
        }

        int[] counts = binCounts(values, n, lo, hi, bins);

        PrintStream out = System.out;
        boolean closeOut = false;
        if (outfile != null) {
            try {
                out = new PrintStream(outfile);
            } catch (FileNotFoundException e) {
                fail("could not write " + outfile);
            }
            closeOut = true;
        }
        printHistogram(counts, lo, hi, label, n, width, out);
        if (closeOut) {
            out.close();
        }
    }

    public static int[] binCounts(double[] values, int n, double lo, double hi,
                                  int bins) {
        int[] counts = new int[bins];
        double binWidth = (hi - lo) / bins;
        for (int i = 0; i < n; i++) {
            int b = (int) ((values[i] - lo) / binWidth);
            if (b >= bins) {
                b = bins - 1;
            }
            counts[b]++;
        }
        return counts;
    }

    public static void printHistogram(int[] counts, double lo, double hi,
                                      String label, int total, int maxBarWidth,
                                      PrintStream out) {
        int bins = counts.length;
        double binWidth = (hi - lo) / bins;

        int maxCount = 0;
        for (int c : counts) {
            if (c > maxCount) {
                maxCount = c;
            }
        }

        out.printf("Histogram of \"%s\"  (%d values, %d bins)%n",
            label, total, bins);
        for (int i = 0; i < bins; i++) {
            double binLo = lo + i * binWidth;
            double binHi = (i == bins - 1) ? hi : lo + (i + 1) * binWidth;
            char close = (i == bins - 1) ? ']' : ')';
            int barLen = (maxCount == 0) ? 0
                : (int) Math.round((double) counts[i] / maxCount * maxBarWidth);
            out.printf(" [%6.2f, %6.2f%c:%4d  %s%n",
                binLo, binHi, close, counts[i], "*".repeat(barLen));
        }
    }

    private static double min(double[] a, int n) {
        double m = a[0];
        for (int i = 1; i < n; i++) {
            if (a[i] < m) {
                m = a[i];
            }
        }
        return m;
    }

    private static double max(double[] a, int n) {
        double m = a[0];
        for (int i = 1; i < n; i++) {
            if (a[i] > m) {
                m = a[i];
            }
        }
        return m;
    }

    private static void requireValue(String[] args, int i, String flag) {
        if (i + 1 >= args.length) {
            fail("missing value for " + flag);
        }
    }

    private static int parseFlagInt(String value, String flag) {
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            fail(flag + " must be an integer, got: " + value);
            return 0;
        }
    }

    private static void fail(String message) {
        System.err.println("Histogram: " + message);
        System.exit(1);
    }
}
