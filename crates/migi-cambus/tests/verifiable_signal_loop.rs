use migi_cambus::{receive_one_tcp, send_tcp, SymbolPacket};
use migi_chainlog::{ChainLog, GENESIS_RECEIPT_REF};
use migi_core::{issue_receipt, Actor, ActorType, Authority, MuefEvent, SourceClass, TreLogic};
use std::net::TcpListener;
use std::thread;

#[test]
fn node_a_to_node_b_is_replayable_and_verifiable() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap();

    let node_b = thread::spawn(move || {
        let packet = receive_one_tcp(&listener).expect("node-b receives CAMbus packet");

        let authority = Authority {
            tre_logic: TreLogic::Proceed,
            reason_code: "local_test_signal_allowed".into(),
            consent_scope: Some("migi-cs-001".into()),
        };

        let observation = serde_json::json!({
            "accepted": true,
            "executed_by": "node-b",
            "event_id": packet.event.event_id.clone()
        });
        let receipt = issue_receipt(
            &packet.event,
            authority,
            &observation,
            GENESIS_RECEIPT_REF,
        )
        .expect("node-b issues receipt");

        let mut chainlog = ChainLog::open_memory().expect("chainlog opens");
        chainlog
            .append(packet.event, observation, receipt)
            .expect("verified entry appends");
        chainlog.verify().expect("chain verifies");
        let replayed = chainlog.replay().expect("state replays");

        (
            chainlog.len().unwrap(),
            replayed.values.get("mode").cloned(),
            replayed.applied_entries,
            replayed.head_receipt_id,
        )
    });

    let actor = Actor {
        actor_type: ActorType::Service,
        id: "node-a".into(),
    };
    let mut event = MuefEvent::new("migi.state.patch", actor, SourceClass::Original);
    event
        .payload
        .insert("state_patch".into(), serde_json::json!({"mode": "active"}));

    let packet = SymbolPacket::new("node-a", "node-b", event);
    send_tcp(&address.to_string(), &packet).expect("node-a sends CAMbus packet");

    let (entries, mode, applied_entries, head_receipt) = node_b.join().unwrap();
    assert_eq!(entries, 1);
    assert_eq!(mode, Some(serde_json::json!("active")));
    assert_eq!(applied_entries, 1);
    assert!(head_receipt.is_some());
}
