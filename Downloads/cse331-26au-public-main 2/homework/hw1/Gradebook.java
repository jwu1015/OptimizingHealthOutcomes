/**
 * Reads a gradebook spread across three CSV files and writes each student's
 * weighted course grade.
 *
 * Usage:
 *   java Gradebook [-o OUTFILE] ASSIGNMENTS_FILE CATEGORIES_FILE GRADES_FILE
 *
 * Inputs:
 *   ASSIGNMENTS_FILE  filename of the CSV file describing the assignments'
 *                     categories
 *   CATEGORIES_FILE   filename of the CSV file describing the categories'
 *                     drop policy and weight
 *   GRADES_FILE       filename of the CSV file containing student grades
 *
 * All three CSV files have a header row, consisting of the column names.
 *
 * The assignments file has two columns: assignment and category. There is one
 * non-header row for each assignment in the course. The first column is the
 * name of the assignment. The second column is that assignment's category. (See
 * assignments.csv for an example.)
 *
 * The categories file has three columns: category, weight, and drop. There is
 * one non-header row for each category. The first column is the name of the
 * category. The second column is that category's percentage contribution to the
 * course grade. And the third column is the number of assignment grades to drop
 * from that category.
 *
 * The grades file has N+1 columns, where N is the number of assignments. The
 * first column's name is "student". Subsequent columns then give the names of
 * all the assignments in the course. It has one non-header row per student. The
 * student's row contains their name in the first column and then their grades
 * in all the assignments in subsequent columns. (See grades.csv for an
 * example.)
 *
 * There are a number of requirements on the input data:
 * - Each file has the expected header row.
 * - In each input file, every row must have the same number of columns.
 * - The values in the weight column of the categories sum to 100.
 * - Every non-student column in the grades file names an assignment in the
 *   assignments file.
 * - Every category named by the assignments file exists in the categories file.
 * - The number of assignments to be dropped from a category must be strictly
 *   less than the total number of assignments in that category.
 * - Every category has at least one assignment in it.
 * - The values in the weight and drop columns of the categories file must
 *   be non-negative integers.
 * - All grades must be integers between 0 and 100 (inclusive on both ends).
 *
 * If any of these conditions is not met, an error is printed and the program
 * exits.
 *
 * For each student, their course grade is computed as follows:
 *   - Apply each category's drop policy by dropping the number of
 *     assignments specified in the categories file.
 *   - Compute the per-category average grade excluding dropped assignments.
 *   - The course grade is the weighted sum of the category averages using
 *     the weights specified in the categories file.
 *
 * The course grade is a decimal number between 0 and 100, rounded to exactly
 * two decimal places.
 *
 * The output is itself a CSV: a header row "student,grade", then one row per
 * student giving the student's name and course grade (for example, "Maya,91.17"),
 * in the same order the students appear in the grades file. By default the output
 * is printed to standard output; if "-o OUTFILE" is given, it is written to
 * OUTFILE instead. (See expected_output.csv for the output on the example input.)
 */
public class Gradebook {

    /**
     * Returns the index of a minimum element in a range.
     *
     * @requires 0 <= lo < hi <= a.length
     * @return an index i with lo <= i < hi holding the smallest value in
     *     a[lo..hi]. If the smallest value appears more than once, any of those
     *     occurrences might be returned.
     */
    public static int indexOfMin(int[] a, int lo, int hi) {
        // You are *not* required to implement this method.
        throw new UnsupportedOperationException(
            "indexOfMin is provided by the staff at grading time");
    }

    /**
     * Drops the k lowest-valued scores from the used prefix scores[0..n].
     *
     * @requires 0 <= k <= n <= scores.length
     * @modifies scores
     * @effects removes the k smallest values of scores[0..n], leaving the
     *     remaining n-k values in scores[0..n-k] in an unspecified order;
     *     the values of scores[n-k..n] are unspecified
     */
    public static void dropLowest(int[] scores, int n, int k) {
        // TODO: implement this method to meet the specification above.
        // You must call indexOfMin() given above.
        throw new RuntimeException("dropLowest is not implemented yet");
    }

    /**
     * Computes every student's weighted course grade.
     *
     * @param assignments the data from the ASSIGNMENTS_FILE, including its header
     * @param categories the data from the CATEGORIES_FILE, including its header
     * @param grades the data from the GRADES_FILE, including its header
     * @requires all three grids are rectangular
     * @requires every assignment named in the grades header appears in assignments
     * @requires every category named in the assignments file exists in the
     *     categories file
     * @requires every score cell parses as an int between 0 and 100
     * @requires every weight is a nonnegative int and the weights sum to 100
     * @requires every drop parses as a non-negative int
     * @requires for each category c, the requested number of assignments to drop
     *     from c must be strictly less than the total number of assignments in c
     * @return a new array of length grades.length - 1, where the ith element is
     *     the course grade of the student in grades row i+1
     */
    public static double[] computeCourseGrades(
        String[][] assignments, String[][] categories, String[][] grades
    ) {
        // You are *not* required to implement this method.
        throw new UnsupportedOperationException(
            "computeCourseGrades is provided by the staff at grading time");
    }

    public static void main(String[] args) {
        // TODO: implement this method to meet the specification above.
        throw new RuntimeException("main is not implemented yet");


        // Hint: refer to Histogram.java to see how to handle command line
        // options, parse a CSV file, validate inputs, and write outputs to a
        // file or stdout depending on whether an output file was given.
    }

}
