import csv
import matplotlib.pyplot as plt
import statistics

scores = []
times = []
difficulties = []

with open("game_data.csv", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        scores.append(int(row["Score"]))
        times.append(int(row["Total Time (s)"]))
        difficulties.append(float(row["Difficulty"]))

print("===== STATISTICAL SUMMARY =====")
print("Total Sessions:", len(scores))
print("Average Score:", round(statistics.mean(scores),2))
print("Median Score:", statistics.median(scores))
print("Average Survival Time:", round(statistics.mean(times),2))
print("Average Difficulty:", round(statistics.mean(difficulties),2))

plt.figure()
plt.plot(difficulties)
plt.title("Difficulty Evolution")
plt.xlabel("Session")
plt.ylabel("Difficulty Multiplier")
plt.show()

plt.figure()
plt.scatter(times, scores)
plt.title("Score vs Survival Time")
plt.xlabel("Time (s)")
plt.ylabel("Score")
plt.show()