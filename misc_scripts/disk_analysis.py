import logging
import os
import shutil
import subprocess
from collections import defaultdict

import psutil


def check_disk_usage(path="/"):
    total, used, free = shutil.disk_usage(path)
    logging.info(f"Total: {total // (2**30)} GiB")
    logging.info(f"Used: {used // (2**30)} GiB")
    logging.info(f"Free: {free // (2**30)} GiB")


def list_large_files(path="/", top_n=10):
    files = []
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(fp)
                files.append((size, fp))
            except OSError:
                logging.warning(f"Unable to get size of {fp}")

    files.sort(reverse=True)
    logging.info("Top %d largest files:", top_n)
    for size, fp in files[:top_n]:
        logging.info(f"{size // (2**20)} MiB: {fp}")


def analyze_folder_sizes(path="/", top_n=10):
    folder_sizes = defaultdict(int)

    for dirpath, dirnames, filenames in os.walk(path):
        try:
            folder_size = sum(
                os.path.getsize(os.path.join(dirpath, f)) for f in filenames
            )
            folder_sizes[dirpath] = folder_size
        except OSError:
            logging.warning(f"Unable to analyze folder {dirpath}")

    sorted_folders = sorted(folder_sizes.items(), key=lambda x: x[1], reverse=True)

    logging.info("Top %d largest folders:", top_n)
    for folder, size in sorted_folders[:top_n]:
        logging.info(f"{size // (2**20)} MiB: {folder}")


def get_open_files():
    logging.info("Open files by processes:")
    for proc in psutil.process_iter(["pid", "name", "open_files"]):
        try:
            if proc.info["open_files"]:
                logging.info(f"Process {proc.info['pid']} ({proc.info['name']}):")
                for file in proc.info["open_files"]:
                    logging.info(f"  {file.path}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def get_disk_io_stats():
    io_counters = psutil.disk_io_counters()
    logging.info("Disk I/O Statistics:")
    logging.info(f"Read count: {io_counters.read_count}")
    logging.info(f"Write count: {io_counters.write_count}")
    logging.info(f"Read bytes: {io_counters.read_bytes // (2**20)} MiB")
    logging.info(f"Write bytes: {io_counters.write_bytes // (2**20)} MiB")


def get_swap_info():
    swap = psutil.swap_memory()
    logging.info("Swap Information:")
    logging.info(f"Total: {swap.total // (2**20)} MiB")
    logging.info(f"Used: {swap.used // (2**20)} MiB")
    logging.info(f"Free: {swap.free // (2**20)} MiB")
    logging.info(f"Percent: {swap.percent}%")


def get_file_system_info():
    logging.info("File System Information:")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        logging.info(f"Device: {partition.device}")
        logging.info(f"  Mountpoint: {partition.mountpoint}")
        logging.info(f"  File system type: {partition.fstype}")
        logging.info(f"  Options: {partition.opts}")


def get_largest_open_files(top_n=10):
    logging.info(f"Top {top_n} largest open files:")
    try:
        output = subprocess.check_output(
            ["lsof", "-n", "-s", "-F", "n", "-o"], universal_newlines=True
        )
        files = []
        for line in output.split("\n"):
            if line.startswith("n/"):
                try:
                    size = os.path.getsize(line[2:])
                    files.append((size, line[2:]))
                except OSError:
                    pass
        files.sort(reverse=True)
        for size, path in files[:top_n]:
            logging.info(f"{size // (2**20)} MiB: {path}")
    except subprocess.CalledProcessError:
        logging.error(
            "Unable to get information about open files. Make sure you have necessary permissions."
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root_path = "/"  # Adjust this if you want to analyze a specific directory

    logging.info("Disk Usage Information:")
    check_disk_usage(root_path)

    logging.info("\nLargest Files:")
    list_large_files(root_path)

    logging.info("\nLargest Folders:")
    analyze_folder_sizes(root_path)

    logging.info("\nOpen Files by Processes:")
    get_open_files()

    logging.info("\nDisk I/O Statistics:")
    get_disk_io_stats()

    logging.info("\nSwap Information:")
    get_swap_info()

    logging.info("\nFile System Information:")
    get_file_system_info()

    logging.info("\nLargest Open Files:")
    get_largest_open_files()


if __name__ == "__main__":
    main()
