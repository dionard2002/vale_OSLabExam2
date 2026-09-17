"""
CPU Scheduling Simulator + Banker's Algorithm
------------------------------------------------
Implements:
  1. First Come First Serve (FCFS)      - Non-preemptive
  2. Round Robin (RR)                   - Preemptive
  3. Banker's Algorithm                 - Safe state check

All input is taken from the console. Run with:  python scheduling_sim.py
"""

# ----------------------------------------------------------------------
# Helper: print a text-based Gantt Chart
# ----------------------------------------------------------------------
def print_gantt_chart(timeline):
    """
    timeline: list of tuples (process_label, start_time, end_time)
    Draws something like:

    |  P1  |  P2  |  P1  |  P3  |
    0      4      7      10     14
    """
    if not timeline:
        print("(no processes to schedule)")
        return

    # Top bar with process labels
    top = "|"
    for label, start, end in timeline:
        width = max(len(label) + 2, len(str(end)) + 1)
        top += f"{label:^{width}}|"
    print(top)

    # Bottom bar with time markers
    bottom = ""
    pos = 0
    for label, start, end in timeline:
        width = max(len(label) + 2, len(str(end)) + 1)
        time_str = str(start)
        bottom += time_str + " " * (width + 1 - len(time_str))
        pos += width + 1
    bottom += str(timeline[-1][2])
    print(bottom)
    print()


# ----------------------------------------------------------------------
# 1. FCFS (Non-preemptive)
# ----------------------------------------------------------------------
def fcfs_scheduling(processes):
    """
    processes: list of dicts {'pid': str, 'arrival': int, 'burst': int}
    Returns the timeline, and fills in completion/waiting/turnaround times.
    """
    # Sort by arrival time, ties broken by original order (stable sort)
    order = sorted(processes, key=lambda p: (p['arrival'], p['pid']))

    time = 0
    timeline = []
    for p in order:
        start = max(time, p['arrival'])
        end = start + p['burst']
        timeline.append((p['pid'], start, end))

        p['completion'] = end
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']

        time = end

    return timeline


# ----------------------------------------------------------------------
# 2. Round Robin (Preemptive)
# ----------------------------------------------------------------------
def round_robin_scheduling(processes, quantum):
    """
    processes: list of dicts {'pid': str, 'arrival': int, 'burst': int}
    quantum: int, time slice
    Returns the timeline (may contain multiple entries per process).
    """
    # Work on copies so original burst values are preserved for reporting
    remaining = {p['pid']: p['burst'] for p in processes}
    n = len(processes)
    completed = {p['pid']: False for p in processes}
    completion = {}

    # Sort by arrival for the initial ready-queue fill order
    procs_sorted = sorted(processes, key=lambda p: (p['arrival'], p['pid']))

    time = 0
    queue = []
    timeline = []
    in_queue = set()
    idx = 0  # pointer into procs_sorted for processes not yet arrived

    # Start the clock at the first arrival
    if procs_sorted:
        time = procs_sorted[0]['arrival']

    # Add any processes that have arrived by current time
    def enqueue_arrivals(current_time):
        nonlocal idx
        while idx < n and procs_sorted[idx]['arrival'] <= current_time:
            pid = procs_sorted[idx]['pid']
            if pid not in in_queue and not completed[pid]:
                queue.append(pid)
                in_queue.add(pid)
            idx += 1

    enqueue_arrivals(time)

    lookup = {p['pid']: p for p in processes}

    while len(queue) > 0:
        pid = queue.pop(0)
        in_queue.discard(pid)

        run_time = min(quantum, remaining[pid])
        start = time
        end = start + run_time
        timeline.append((pid, start, end))

        time = end
        remaining[pid] -= run_time

        # Any processes that arrived DURING this run should be enqueued
        # before we decide whether to re-queue the just-run process
        enqueue_arrivals(time)

        if remaining[pid] > 0:
            queue.append(pid)
            in_queue.add(pid)
        else:
            completed[pid] = True
            completion[pid] = time

        # If queue is empty but not all processes have arrived, jump time
        if len(queue) == 0 and idx < n:
            time = max(time, procs_sorted[idx]['arrival'])
            enqueue_arrivals(time)

    for p in processes:
        p['completion'] = completion[p['pid']]
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']

    return timeline


# ----------------------------------------------------------------------
# Shared: print process table + averages
# ----------------------------------------------------------------------
def print_results(processes, timeline, title):
    print(f"\n=== {title} ===\n")
    print("Gantt Chart:")
    print_gantt_chart(timeline)

    print(f"{'PID':<8}{'Arrival':<10}{'Burst':<8}{'Completion':<12}{'Waiting':<10}{'Turnaround':<12}")
    total_wait = 0
    total_turn = 0
    for p in sorted(processes, key=lambda x: x['pid']):
        print(f"{p['pid']:<8}{p['arrival']:<10}{p['burst']:<8}{p['completion']:<12}"
              f"{p['waiting']:<10}{p['turnaround']:<12}")
        total_wait += p['waiting']
        total_turn += p['turnaround']

    n = len(processes)
    print(f"\nAverage Waiting Time:    {total_wait / n:.2f}")
    print(f"Average Turnaround Time: {total_turn / n:.2f}\n")


# ----------------------------------------------------------------------
# Console input helpers
# ----------------------------------------------------------------------
def get_processes_from_console():
    while True:
        try:
            n = int(input("Enter number of processes: "))
            if n > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid integer.")

    processes = []
    for i in range(n):
        pid = f"P{i + 1}"
        while True:
            try:
                arrival = int(input(f"Enter arrival time for {pid}: "))
                burst = int(input(f"Enter burst time for {pid}: "))
                if arrival < 0 or burst <= 0:
                    print("Arrival must be >= 0 and burst must be > 0.")
                    continue
                break
            except ValueError:
                print("Please enter valid integers.")
        processes.append({'pid': pid, 'arrival': arrival, 'burst': burst})
    return processes


def run_fcfs():
    processes = get_processes_from_console()
    timeline = fcfs_scheduling(processes)
    print_results(processes, timeline, "First Come First Serve (FCFS)")


def run_round_robin():
    processes = get_processes_from_console()
    while True:
        try:
            quantum = int(input("Enter time quantum: "))
            if quantum > 0:
                break
            print("Time quantum must be > 0.")
        except ValueError:
            print("Please enter a valid integer.")

    timeline = round_robin_scheduling(processes, quantum)
    print_results(processes, timeline, f"Round Robin (Quantum = {quantum})")


# ----------------------------------------------------------------------
# 3. Banker's Algorithm
# ----------------------------------------------------------------------
def get_matrix(rows, cols, label):
    print(f"\nEnter {label} matrix ({rows} rows x {cols} columns).")
    print("Enter each row as space-separated integers.")
    matrix = []
    for i in range(rows):
        while True:
            try:
                row = list(map(int, input(f"  {label} for P{i}: ").split()))
                if len(row) != cols:
                    print(f"  Please enter exactly {cols} values.")
                    continue
                if any(v < 0 for v in row):
                    print("  Values must be non-negative.")
                    continue
                matrix.append(row)
                break
            except ValueError:
                print("  Please enter valid integers separated by spaces.")
    return matrix


def bankers_algorithm(n, m, allocation, maximum, available):
    """
    n: number of processes
    m: number of resource types
    allocation: n x m matrix
    maximum: n x m matrix
    available: list of length m

    Returns (is_safe: bool, safe_sequence: list of process indices)
    """
    # Need[i][j] = Maximum[i][j] - Allocation[i][j]
    need = [[maximum[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]

    work = available[:]
    finish = [False] * n
    safe_sequence = []

    progress = True
    while progress and len(safe_sequence) < n:
        progress = False
        for i in range(n):
            if not finish[i]:
                if all(need[i][j] <= work[j] for j in range(m)):
                    # Process i can finish; reclaim its resources
                    for j in range(m):
                        work[j] += allocation[i][j]
                    finish[i] = True
                    safe_sequence.append(i)
                    progress = True

    is_safe = all(finish)
    return is_safe, safe_sequence, need


def run_bankers_algorithm():
    while True:
        try:
            n = int(input("Enter number of processes: "))
            m = int(input("Enter number of resource types: "))
            if n > 0 and m > 0:
                break
            print("Both values must be positive.")
        except ValueError:
            print("Please enter valid integers.")

    allocation = get_matrix(n, m, "Allocation")
    maximum = get_matrix(n, m, "Maximum")

    print(f"\nEnter Available resources ({m} values, space-separated):")
    while True:
        try:
            available = list(map(int, input("  Available: ").split()))
            if len(available) != m:
                print(f"  Please enter exactly {m} values.")
                continue
            break
        except ValueError:
            print("  Please enter valid integers separated by spaces.")

    is_safe, safe_sequence, need = bankers_algorithm(n, m, allocation, maximum, available)

    print("\n=== Banker's Algorithm Result ===\n")
    print(f"{'PID':<8}{'Allocation':<20}{'Max':<20}{'Need':<20}")
    for i in range(n):
        print(f"P{i:<7}{str(allocation[i]):<20}{str(maximum[i]):<20}{str(need[i]):<20}")

    if is_safe:
        seq_str = " -> ".join(f"P{i}" for i in safe_sequence)
        print(f"\nThe system IS in a SAFE state.")
        print(f"Safe Sequence: {seq_str}\n")
    else:
        print("\nThe system is in an UNSAFE state (no safe sequence exists).\n")


# ----------------------------------------------------------------------
# Main menu
# ----------------------------------------------------------------------
def main():
    while True:
        print("=" * 50)
        print(" CPU SCHEDULING & BANKER'S ALGORITHM SIMULATOR")
        print("=" * 50)
        print("1. First Come First Serve (FCFS) - Non-preemptive")
        print("2. Round Robin (RR) - Preemptive")
        print("3. Banker's Algorithm - Safe State Check")
        print("4. Exit")

        choice = input("\nSelect an option (1-4): ").strip()

        if choice == "1":
            run_fcfs()
        elif choice == "2":
            run_round_robin()
        elif choice == "3":
            run_bankers_algorithm()
        elif choice == "4":
            print("Exiting program. Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-4.\n")


if __name__ == "__main__":
    main()