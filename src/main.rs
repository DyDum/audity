#![warn(clippy::pedantic)]
#![warn(clippy::all)]
#![warn(clippy::nursery)]
use audity::controller;
use clap::{Arg, ArgAction, Command};

fn main() {
    let matches: clap::ArgMatches = Command::new("Audity")
        .version("0.1.0")
        .author("DyDum & Wikkizs")
        .about("Linux server scanning and auditing tool")
        .arg_required_else_help(true)
        .arg(Arg::new("audit").short('A').long("audit").help("Run full audit (Must be sudo)").action(ArgAction::SetTrue))
        .arg(Arg::new("package").short('P').long("package").help("Run package audit (Must be sudo)").action(ArgAction::SetTrue))
        .arg(Arg::new("update").short('D').long("update").help("Update package list (Must be sudo)").action(ArgAction::SetTrue).requires("package"))
        .arg(Arg::new("upgrade").short('G').long("upgrade").help("Check upgrades").action(ArgAction::SetTrue).requires("package"))
        .arg(Arg::new("cis").short('C').long("cis").help("Check CIS compliances (MUST HAVE PACKAGE LIST)").action(ArgAction::SetTrue).requires("package"))
        .arg(Arg::new("list").short('L').long("list").help("List all CIS available in audity").action(ArgAction::SetTrue).requires("cis"))
        .arg(Arg::new("filter").short('F').long("filter").help("Filter the audit to a specific package").num_args(1).value_name("CIS_NAME").requires("cis"))
        .arg(Arg::new("correction").short('R').long("correction").help("Correct all packages for CIS compliances (MUST HAVE PACKAGE LIST) (Must be sudo)").action(ArgAction::SetTrue))
        .get_matches();

    let do_update: bool = matches.get_flag("update");
    let do_upgrade: bool = matches.get_flag("upgrade");

    if matches.get_flag("audit") {
        controller::run_full_audit();
    } else if matches.get_flag("cis") {
        if matches.get_flag("list") {
            controller::list_cis();
        }else {
            controller::run_package_audit(do_update, do_upgrade);

            let filter: Option<&str> = matches.get_one::<String>("filter").map(|s| s.as_str());
            controller::run_audit_rules(filter);
        }
        
    } else if matches.get_flag("correction") {
        controller::run_correction();
    } else if matches.get_flag("package") {
        controller::run_package_audit(do_update, do_upgrade);
    }
}
