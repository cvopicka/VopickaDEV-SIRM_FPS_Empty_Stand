#! /usr/bin/env python3

# region - Dependencies
try:
    errstat = False
    __dependencies__ = []

    trying = "logging"
    __dependencies__.append(trying)
    import logging

    trying = "sys"
    __dependencies__.append(trying)
    import sys

    assert sys.version_info >= (
        3,
        6,
    ), f"Incorrect Python version -- {sys.version_info} -- must be at least 3.6"

    trying = "pathlib"
    __dependencies__.append(trying)
    from pathlib import PurePath

    trying = "pyodbc"
    __dependencies__.append(trying)
    import pyodbc

    trying = "pywebio"
    __dependencies__.append(trying)
    from pywebio import (
        input as webinput,
        output as weboutput,
        exceptions as webexceptions,
    )

    trying = "pywebio_battery"
    __dependencies__.append(trying)
    from pywebio_battery import confirm

    trying = "platform"
    __dependencies__.append(trying)
    import platform

    if platform.system() == "windows":
        trying = "asyncio"
        __dependencies__.append(trying)
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    trying = "sirm_spf_libs"
    __dependencies__.append(trying)
    from sirm_spf_libs.Config.DatabaseDSN import database_dsn

    trying = "toml"
    __dependencies__.append(trying)
    from toml import load as toml_load

    trying = "datetime"
    __dependencies__.append(trying)
    from datetime import datetime

except ImportError:
    errstat = True
finally:
    # DOC - Configure the logging system

    # REM - Path tricks for making executable file
    if getattr(sys, "frozen", False):
        runfrom = sys.executable
    else:
        runfrom = __file__

    logging.basicConfig(
        filename=PurePath(
            PurePath(sys.argv[0]).parent / "Logs",
            f"{PurePath(sys.argv[0]).stem}.log",
        ),
        format="%(asctime)s-[%(levelname)s]-(%(filename)s)-<%(funcName)s>-#%(lineno)d#-%(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
        filemode="w",
        level=logging.WARNING,
    )

    # REM - Configure a named logger to NOT use the root log
    logger = logging.getLogger(sys.argv[0].replace(".py", ""))
    logger.setLevel(logging.DEBUG)

    # REM - Configure and add console logging to the named logger
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s-[%(levelname)s]-%(message)s"))
    logger.addHandler(console)

    if errstat is True:
        logger.fatal("Find missing library! -->%s<--", trying)
        raise SystemExit(f"Find missing library! -->{trying}<--")

    # REM - Clean up
    del trying
    del errstat
# endregion - Dependencies

# region Header Block #########################################################
__project__ = runfrom
__purpose__ = "Dealing with empty stands when FPS doesn't"
__license__ = "BSD3"
__maintainer__ = "Charles E. Vopicka"
__email__ = "chuck@vopicka.dev"

# __status__ = "Prototype"
__status__ = "Development"
# __status__ = "Production"

__revisionhistory__ = [
    ["Date", "Type", "Author", "Comment"],
    ["2023.08.20", "Created", __maintainer__, "Script Created"],
]
__created__ = __revisionhistory__[1][0]
__author__ = __revisionhistory__[1][2]
__version__ = __revisionhistory__[len(__revisionhistory__) - 1][0]
if (
    __created__.split(
        ".",
        maxsplit=1,
    )[0]
    != __version__.split(
        ".",
        maxsplit=1,
    )[0]
):
    __copyright__ = f'Copyright {__created__.split(".", maxsplit=1)[0]} - {__version__.split(".", maxsplit=1)[0]}, {__maintainer__}'
else:
    __copyright__ = (
        f'Copyright {__created__.split(".", maxsplit=1)[0]}, {__maintainer__}'
    )

__copyrightstr__ = "This program is licensed under the BSD 3 Clause license\n\n"
__copyrightstr__ += "See the LICENSE file for more information"

__credits__ = []
for n, x in enumerate(__revisionhistory__):
    if x[2] not in __credits__ and n > 0:
        __credits__.append(x[2])

appcredits = "\n".join(
    (
        __purpose__,
        f"\nBy:\t{__author__}",
        f"\t{__email__}",
        "",
        f"License:\t{__license__}",
        "",
        __copyright__,
        "",
        __copyrightstr__,
        f"\nCreated:\t{__created__}",
        f"Version:\t{__version__} ({__status__})",
        f"Rev:\t\t{len(__revisionhistory__) - 1}",
    )
)

logger.info("\n\n%s\n", appcredits)
weboutput.put_html(f"<h1>{__purpose__}</h1>")
weboutput.put_info(appcredits)

# endregion Header Block ######################################################


# region - Functions here


# DOC - Check if Admin_Meta exists
def exist_admin_meta() -> bool:
    """Check if the database contains Admin_Meta

    Returns:
        bool: Success or failure
    """

    with pyodbc.connect(
        f"Driver={{{databasedsn['DRIVER']}}};"
        f"Dbq={PurePath(databasedsn['DBQ'])};"
        f"Uid={databasedsn['UID']};"
        f"Pwd=;"
    ) as dbconn:
        with dbconn.cursor() as dbcurs:
            if dbcurs.tables(
                table="Admin_Meta",
                tableType="TABLE",
            ).fetchone():
                return True
            else:
                return False


def what_to_do():
    """Evaluate user's needs

    Raises:
        SystemExit: Session closed
        SystemExit: User exited
        SystemError: Unknown response
    """
    try:
        filltype = webinput.radio(
            "What type of operation do you want?",
            [
                ("NONE / EXIT", None, True, False),
                ("STAND Only", 1, False, False),
                ("STAND & DBHCLS", 2, False, False),
            ],
        )
    except webexceptions.SessionClosedException as ex:
        # REM - User closed the browser
        logger.info("User chose to exit.  GOODBYE!")
        raise SystemExit from ex

    if filltype is None:
        # REM - User asked to exit
        weboutput.put_success("User chose to exit.  GOODBYE!")
        raise SystemExit
    elif filltype in [
        1,
        2,
    ]:
        # REM - STAND
        defaultstandyear = webinput.input(
            "Default year if not in Admin_Meta?",
            webinput.NUMBER,
            value=datetime.now().year,
        )
        stands = builder_stand(defaultstandyear)
    else:
        # REM - Unknown selection
        raise SystemError

    if filltype == 2:
        # REM - DBHCLS
        builder_dbhcls(stands)


def builder_stand(standyear: int) -> list:
    """Insert EMPTY stands into the STAND table

    Args:
        standyear (int): Default year to create stand as defined by user input

    Raises:
        SystemExit: Exit on user termination

    Returns:
        list: list of completed stands for the DBHCLS function if selected
    """
    standstoprocess = []
    standstoreturn = []

    with pyodbc.connect(
        f"Driver={{{databasedsn['DRIVER']}}};"
        f"Dbq={PurePath(databasedsn['DBQ'])};"
        f"Uid={databasedsn['UID']};"
        f"Pwd=;"
    ) as dbconn:
        with dbconn.cursor() as dbcurs:
            dbcurs.execute(sqlstrings["SQL"]["candidate_stands"])

            standstoprocess = [  # List comprehension
                (
                    list(x) if x[1] not in [None, 0] else [x[0], standyear]
                )  # Correct Harvest Yr if empty or zero
                for x in dbcurs.fetchall()
            ]

            if confirm(
                "Processing the following stands?",
                ", ".join([str(x[0]) for x in standstoprocess]),
            ) in [None, False]:
                weboutput.put_info("User terminated")
                logger.info("User terminated")
                raise SystemExit

            for stand in standstoprocess:
                dbcurs.execute(
                    sqlstrings["SQL"]["check_stand"],
                    (stand[0],),
                )
                if dbcurs.fetchall() == []:
                    stand.append(999)
                    dbcurs.execute(
                        sqlstrings["SQL"]["append_stand"],
                        stand,
                    )
                    dbcurs.execute(
                        sqlstrings["SQL"]["update_admin"],
                        (
                            stand[1],
                            stand[0],
                        ),
                    )
                    weboutput.put_success(f"Appended {stand[0]} to STAND")
                    logger.info("Appended %s to STAND", stand[0])
                    standstoreturn.append(
                        [
                            stand[0],
                            stand[1],
                        ]
                    )
                else:
                    weboutput.put_error(
                        f"{stand[0]} already existed in STAND skipping {stand[0]}"
                    )
                    logger.info(
                        "%s already existed in STAND skipping %s",
                        stand[0],
                        stand[0],
                    )

    return standstoreturn


def builder_dbhcls(stands: list) -> None:
    """INSERT empty DBHCLS records

    Args:
        stands (list): List of stands with date
    """
    with pyodbc.connect(
        f"Driver={{{databasedsn['DRIVER']}}};"
        f"Dbq={PurePath(databasedsn['DBQ'])};"
        f"Uid={databasedsn['UID']};"
        f"Pwd=;"
    ) as dbconn:
        with dbconn.cursor() as dbcurs:
            for stand in stands:
                dbcurs.execute(
                    sqlstrings["SQL"]["check_dbhcls"],
                    (stand[0],),
                )

                if dbcurs.fetchall() == []:
                    dbcurs.execute(
                        sqlstrings["SQL"]["append_dbhcls"],
                        stand,
                    )
                    weboutput.put_success(f"Appended {stand[0]} to DBHCLS")
                    logger.info("Appended %s to DBHCLS", stand[0])
                else:
                    weboutput.put_error(
                        f"{stand[0]} already existed in DBHCLS skipping {stand[0]}"
                    )
                    logger.info(
                        "%s already existed in DBHCLS skipping %s",
                        stand[0],
                        stand[0],
                    )


# endregion - End of functions

databasedsn = database_dsn()

sqlstrings = toml_load(
    PurePath(
        PurePath(sys.argv[0]).parent,
        "sql.toml",
    )
)

if __name__ == "__main__":
    if exist_admin_meta():
        weboutput.put_success("Database contains Admin_Meta")
        if confirm("Admin_Meta exists", "Have you configured Admin_Meta?"):
            what_to_do()
        else:
            weboutput.put_error("Please configure Admin_Meta and try again.")
            logger.error("Admin_meta not configured exiting")
            raise SystemExit
        weboutput.put_success("Operation Completed")

    else:
        weboutput.put_error(
            "Admin_Meta NOT DETECTED please configure Admin_Meta and try again."
        )
        logger.error("Admin_Meta not detected exiting")
