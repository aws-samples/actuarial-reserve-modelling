use serde::{Deserialize, Serialize};
use rand::{thread_rng, Rng};
use rand_distr::{Exp, Normal};
use std::io::prelude::*;
use std::{collections::HashMap, env, fs::File};
use std::time::{Instant};
use csv::{Reader};


const NUM_SIMULATIONS: usize = 10_000;
const CLAIM_INTERVAL: f64 = 365.0;


#[derive(Serialize, Deserialize)]
struct Policy {
    id: String,
    age: f64,
    gender: String,
    smoking_status: String,
    occupation: String,
    policy_type: String,
    effective_date: String,
    term: f64,
    premium: f64,
}

#[derive(Serialize, Deserialize)]
struct Claim {
    policy_id: String,
    claim_amount: f64,
    claim_date: String,
}


#[tokio::main]
async fn main() -> Result<(), csv::Error> {

    let start = Instant::now();

    let args: Vec<String> = env::args().collect();
    let input_file = &args[1];
    let output_file = &args[2];

    // Reader from csv file and txt output file
    let mut rdr = Reader::from_path(input_file)?;
    let mut file = File::create(output_file)?;
    
    // Create a policies vector from csv file
    let mut policies = vec![];
    for record in rdr.records() { 
        let policy: Policy = record.unwrap().deserialize(None)?;
        policies.push(policy);
    }

    // Create a map from policy ID to policy data
    let mut policy_map = HashMap::new();
    for policy in &policies {
        policy_map.insert(policy.id.clone(), policy);
    }

    // Run the simulation
    let mut total_reserves = 0.0;
    for _ in 0..NUM_SIMULATIONS {
        let mut reserves = 0.0;
        for policy in &policies {
            // Calculate the number of claims for this policy
            let num_claims = thread_rng().sample(Exp::new(1.0 / (policy.term / CLAIM_INTERVAL)).unwrap());

            // Calculate the reserves for this policy
            for _ in 0..num_claims as usize {
                let claim_amount = thread_rng().sample(Normal::new(100.0, 10.0).unwrap());
                reserves += claim_amount;
            }
        }
        total_reserves += reserves;
    }

    // Calculate the average reserves across all simulations 
    // and write to the output file
    let avg_reserves = total_reserves / NUM_SIMULATIONS as f64;
    file.write_all(avg_reserves.to_string().as_bytes())?;

    let duration = start.elapsed();

    println!("Time elapsed since the start: {:?}", duration);

    Ok(())
}