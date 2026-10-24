import java.util.*;

public class GeneralManager1 {
    /**
     * An individual player in Zach and James's scouting report.
     *
     * @param salary The player's desired salary in millions of dollars.
     *               Must be non-negative.
     * @param name The name of the player. Must not be null or empty.
     */
    public static record Player(String name, int salary) {
        // Example players. You should not assume this list is exhaustive.
        public static final Player ARI = new Player("Ari Waingold", 12);
        public static final Player KYLE = new Player("Kyle Sherman", 15);
        public static final Player PRATIKA = new Player("Pratika Eswaran", 14);
        public static final Player PRANAV = new Player("Pranav Suri", 6);
        public static final Player NAREN = new Player("Naren Ramakrishnan", 20);
        public static final Player OWEN = new Player("Owen Fei", 24);
        public static final Player EMILY = new Player("Emily Calabaza", 18);
        public static final Player YIHONG = new Player("Yihong Zhang", 5);
    }

    /**
     * Build a roster of players using players from the scouting report.
     *
     * @param scoutingReport The players in Zach and James's scouting report.
     *                       Must not be null, and none of the players it
     *                       contains may be null.
     * @param minimumSalary The minimum total salary of the roster in millions
     *                      of dollars. Must be non-negative.
     * @param maximumSalary The maximum total salary of the roster in millions
     *                      of dollars. Must be non-negative.
     * @requires
     *   - minimumSalary <= maximumSalary
     *   - No player occurs in the scouting report more than once.
     *   - The total salary of all players in the scouting report is at least
     *     minimumSalary.
     *   - Every player in the scouting report has salary at most
     *     maximumSalary - minimumSalary.
     * @return A non-null list of players (the roster) such that:
     *   - every player in the roster is from the scouting report, and no
     *     player occurs in the roster more than once
     *   - minimumSalary <= (total salary of the roster) <= maximumSalary
     */
    public static List<Player> buildRoster(
        final Player[] scoutingReport,
        final int minimumSalary,
        final int maximumSalary
    ) {
        // TODO: Write your implementation here.
        return null;
    }
}
