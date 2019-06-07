package util;

/**
 * Primarily a wrapper for holding two integers, but also useful as it passes
 * some methods from MineSweeperBoard
 * 
 * @author  KnightMiner
 */
public class Space {

    private int x, y;

    /**
     * Creates a new space with the specified row and column
     * @param x  X value of the space
     * @param y  Y value of the space
     */
    public Space(int x, int y) {
        this.x = x;
        this.y = y;
    }

    /**
     * Gets the x value
     * @return  The x value
     */
    public int getX() {
        return x;
    }

    /**
     * Gets the y value
     * @return  The y value
     */
    public int getY() {
        return y;
    }

    /**
     * Determines if two spaces are equal
     * @param other  Space to compare
     * @return  true if the two spaces are equal
     */
    public boolean equals(Space other) {
        if(other == null) {
            return false;
        }

        return this.x == other.x
                && this.y == other.y;
    }

    /**
     * Creates a string of the current space
     * @return  a string of the current space
     */
    @Override
    public String toString() {
        return String.format("(%d,%d)", x, y);
    }
}