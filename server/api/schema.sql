-- Schéma PostgreSQL de Kimetsu Pandora.
-- Tiré du modèle docs/DATABASE-SCHEMA.mmd. `transaction` est renommée `transactions` (mot réservé).
-- Ordre de création : les tables référencées d'abord.

CREATE TABLE faction (
    faction_id   INTEGER PRIMARY KEY,
    name         VARCHAR(64) NOT NULL,
    description  TEXT
);

CREATE TABLE player (
    player_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    steam_id      VARCHAR(32) NOT NULL UNIQUE,
    first_name    VARCHAR(64),
    last_name     VARCHAR(64),
    display_name  VARCHAR(64),
    email         VARCHAR(255),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ,
    is_banned     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE admin_role (
    role_id  INTEGER PRIMARY KEY,
    name     VARCHAR(32) NOT NULL UNIQUE
);

CREATE TABLE player_role (
    player_id  UUID    NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    role_id    INTEGER NOT NULL REFERENCES admin_role(role_id) ON DELETE CASCADE,
    PRIMARY KEY (player_id, role_id)
);

CREATE TABLE currency (
    currency_id  INTEGER PRIMARY KEY,
    code         VARCHAR(32) NOT NULL UNIQUE  -- yen, shop_point, faction_token
);

CREATE TABLE shop_order (
    order_id      BIGSERIAL PRIMARY KEY,
    player_id     UUID NOT NULL REFERENCES player(player_id),
    product_code  VARCHAR(64) NOT NULL,
    amount_cents  INTEGER NOT NULL,
    currency_code VARCHAR(8) NOT NULL,
    payment_ref   VARCHAR(128),
    status        VARCHAR(16) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
    tx_id       BIGSERIAL PRIMARY KEY,
    player_id   UUID NOT NULL REFERENCES player(player_id),
    currency_id INTEGER NOT NULL REFERENCES currency(currency_id),
    order_id    BIGINT REFERENCES shop_order(order_id),
    amount      BIGINT NOT NULL,
    reason      VARCHAR(128),
    admin_id    UUID REFERENCES player(player_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE wallet (
    player_id    UUID    NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    currency_id  INTEGER NOT NULL REFERENCES currency(currency_id),
    balance      BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, currency_id)
);

CREATE TABLE sanction (
    sanction_id  SERIAL PRIMARY KEY,
    player_id    UUID NOT NULL REFERENCES player(player_id),
    admin_id     UUID REFERENCES player(player_id),
    type         VARCHAR(16) NOT NULL,
    reason       TEXT,
    starts_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at      TIMESTAMPTZ
);

CREATE TABLE game_log (
    log_id        BIGSERIAL PRIMARY KEY,
    player_id     UUID REFERENCES player(player_id) ON DELETE SET NULL,
    character_id  UUID,
    action        VARCHAR(64) NOT NULL,
    details       JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE characters (
    character_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id             UUID NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    faction_id            INTEGER NOT NULL REFERENCES faction(faction_id),
    name                  VARCHAR(64) NOT NULL,
    level                 INTEGER NOT NULL DEFAULT 1,
    xp                    INTEGER NOT NULL DEFAULT 0,
    reroll_count          INTEGER NOT NULL DEFAULT 0,
    skill_points_unspent  INTEGER NOT NULL DEFAULT 0,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    job                   VARCHAR(32),            -- classe / souffle choisi
    hp                    INTEGER,                -- points de vie actuels
    max_hp                INTEGER,                -- points de vie maximum
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE character_appearance (
    character_id  UUID PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    appearance    JSONB NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE faction_change (
    change_id        BIGSERIAL PRIMARY KEY,
    character_id     UUID NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    from_faction_id  INTEGER NOT NULL REFERENCES faction(faction_id),
    to_faction_id    INTEGER NOT NULL REFERENCES faction(faction_id),
    tx_id            BIGINT REFERENCES transactions(tx_id),
    refunded_points  INTEGER NOT NULL DEFAULT 0,
    source           VARCHAR(16) NOT NULL,  -- ingame_shop, irl_shop, admin
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE skill_tree (
    tree_id     SERIAL PRIMARY KEY,
    faction_id  INTEGER NOT NULL REFERENCES faction(faction_id),
    name        VARCHAR(64) NOT NULL,
    kind        VARCHAR(16) NOT NULL  -- breathing, demon_power
);

CREATE TABLE skill_node (
    skill_id         SERIAL PRIMARY KEY,
    tree_id          INTEGER NOT NULL REFERENCES skill_tree(tree_id) ON DELETE CASCADE,
    parent_skill_id  INTEGER REFERENCES skill_node(skill_id),
    name             VARCHAR(64) NOT NULL,
    description      TEXT,
    required_level   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE character_skill (
    character_id  UUID    NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    skill_id      INTEGER NOT NULL REFERENCES skill_node(skill_id),
    points        INTEGER NOT NULL DEFAULT 0,
    unlocked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (character_id, skill_id)
);

CREATE TABLE gift_roll (
    roll_id           BIGSERIAL PRIMARY KEY,
    character_id      UUID NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    granted_skill_id  INTEGER REFERENCES skill_node(skill_id),
    roll_kind         VARCHAR(16) NOT NULL,
    is_reroll         BOOLEAN NOT NULL DEFAULT FALSE,
    tx_id             BIGINT REFERENCES transactions(tx_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE combat_stats (
    character_id      UUID PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    kills             INTEGER NOT NULL DEFAULT 0,
    deaths            INTEGER NOT NULL DEFAULT 0,
    damage_dealt      BIGINT NOT NULL DEFAULT 0,
    damage_taken      BIGINT NOT NULL DEFAULT 0,
    playtime_seconds  INTEGER NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inventory (
    inventory_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id     UUID NOT NULL UNIQUE REFERENCES player(player_id) ON DELETE CASCADE,
    capacity      INTEGER NOT NULL DEFAULT 50
);

CREATE TABLE item (
    item_id      SERIAL PRIMARY KEY,
    name         VARCHAR(64) NOT NULL,
    category     VARCHAR(32) NOT NULL,  -- weapon, blueprint, crate, material, ...
    rarity       VARCHAR(16),
    description  TEXT,
    stackable    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE item_instance (
    instance_id   BIGSERIAL PRIMARY KEY,
    item_id       INTEGER NOT NULL REFERENCES item(item_id),
    inventory_id  UUID NOT NULL REFERENCES inventory(inventory_id) ON DELETE CASCADE,
    character_id  UUID REFERENCES characters(character_id) ON DELETE SET NULL,  -- NULL = non équipé
    quantity      INTEGER NOT NULL DEFAULT 1,
    durability    INTEGER,
    is_equipped   BOOLEAN NOT NULL DEFAULT FALSE,
    slot          INTEGER,
    source        VARCHAR(32),
    acquired_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE weapon (
    item_id         INTEGER PRIMARY KEY REFERENCES item(item_id) ON DELETE CASCADE,
    weapon_type     VARCHAR(32) NOT NULL,
    base_damage     INTEGER NOT NULL,
    max_durability  INTEGER NOT NULL
);

CREATE TABLE blueprint (
    blueprint_id    SERIAL PRIMARY KEY,
    item_id         INTEGER NOT NULL UNIQUE REFERENCES item(item_id) ON DELETE CASCADE,
    result_item_id  INTEGER NOT NULL REFERENCES item(item_id),
    yen_cost        BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE item_perk (
    perk_id      SERIAL PRIMARY KEY,
    name         VARCHAR(64) NOT NULL,
    description  TEXT
);

CREATE TABLE instance_perk (
    instance_id  BIGINT  NOT NULL REFERENCES item_instance(instance_id) ON DELETE CASCADE,
    perk_id      INTEGER NOT NULL REFERENCES item_perk(perk_id),
    value        DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (instance_id, perk_id)
);

CREATE TABLE equipment_reroll (
    reroll_id    BIGSERIAL PRIMARY KEY,
    instance_id  BIGINT REFERENCES item_instance(instance_id) ON DELETE SET NULL,
    player_id    UUID NOT NULL REFERENCES player(player_id),
    tx_id        BIGINT REFERENCES transactions(tx_id),
    old_perks    JSONB,
    new_perks    JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE crate_type (
    crate_type_id  SERIAL PRIMARY KEY,
    item_id        INTEGER NOT NULL UNIQUE REFERENCES item(item_id) ON DELETE CASCADE,
    name           VARCHAR(64) NOT NULL,
    yen_price      BIGINT NOT NULL
);

CREATE TABLE crate_loot (
    crate_type_id  INTEGER NOT NULL REFERENCES crate_type(crate_type_id) ON DELETE CASCADE,
    item_id        INTEGER NOT NULL REFERENCES item(item_id),
    weight         INTEGER NOT NULL,
    PRIMARY KEY (crate_type_id, item_id)
);

CREATE TABLE crate_open (
    open_id        BIGSERIAL PRIMARY KEY,
    player_id      UUID NOT NULL REFERENCES player(player_id),
    crate_type_id  INTEGER NOT NULL REFERENCES crate_type(crate_type_id),
    won_item_id    INTEGER REFERENCES item(item_id),
    opened_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outfit (
    outfit_id  SERIAL PRIMARY KEY,
    name       VARCHAR(64) NOT NULL,
    slot       VARCHAR(32),
    rarity     VARCHAR(16)
);

CREATE TABLE player_outfit (
    player_id    UUID    NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    outfit_id    INTEGER NOT NULL REFERENCES outfit(outfit_id),
    acquired_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, outfit_id)
);

CREATE TABLE character_outfit (
    character_id  UUID    NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    outfit_id     INTEGER NOT NULL REFERENCES outfit(outfit_id),
    is_equipped   BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (character_id, outfit_id)
);

CREATE TABLE cosmetic (
    cosmetic_id  SERIAL PRIMARY KEY,
    name         VARCHAR(64) NOT NULL,
    type         VARCHAR(32),
    rarity       VARCHAR(16)
);

CREATE TABLE player_cosmetic (
    player_id    UUID    NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    cosmetic_id  INTEGER NOT NULL REFERENCES cosmetic(cosmetic_id),
    acquired_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, cosmetic_id)
);

CREATE TABLE character_cosmetic (
    character_id  UUID    NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    cosmetic_id   INTEGER NOT NULL REFERENCES cosmetic(cosmetic_id),
    is_equipped   BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (character_id, cosmetic_id)
);

CREATE TABLE trade (
    trade_id            BIGSERIAL PRIMARY KEY,
    initiator_player_id UUID NOT NULL REFERENCES player(player_id),
    receiver_player_id  UUID NOT NULL REFERENCES player(player_id),
    status              VARCHAR(16) NOT NULL,
    fee_tx_id           BIGINT REFERENCES transactions(tx_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at           TIMESTAMPTZ
);

CREATE TABLE trade_item (
    trade_id     BIGINT NOT NULL REFERENCES trade(trade_id) ON DELETE CASCADE,
    instance_id  BIGINT NOT NULL REFERENCES item_instance(instance_id),
    PRIMARY KEY (trade_id, instance_id)
);

CREATE TABLE trade_currency (
    trade_id     BIGINT  NOT NULL REFERENCES trade(trade_id) ON DELETE CASCADE,
    offered_by   UUID    NOT NULL REFERENCES player(player_id),
    currency_id  INTEGER NOT NULL REFERENCES currency(currency_id),
    amount       BIGINT  NOT NULL,
    PRIMARY KEY (trade_id, offered_by, currency_id)
);

-- Pas de clé étrangère sur instance_id : l'objet est supprimé quand il est lâché.
CREATE TABLE item_log (
    log_id         BIGSERIAL PRIMARY KEY,
    instance_id    BIGINT,
    player_id      UUID REFERENCES player(player_id) ON DELETE SET NULL,
    to_player_id   UUID REFERENCES player(player_id) ON DELETE SET NULL,
    trade_id       BIGINT REFERENCES trade(trade_id) ON DELETE SET NULL,
    event_type     VARCHAR(16) NOT NULL,  -- dropped, gifted, traded, crafted, ...
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE house (
    house_id  SERIAL PRIMARY KEY,
    name      VARCHAR(64) NOT NULL,
    map_name  VARCHAR(64),
    pos_x     DOUBLE PRECISION,
    pos_y     DOUBLE PRECISION,
    pos_z     DOUBLE PRECISION
);

CREATE TABLE house_instance (
    instance_id      BIGSERIAL PRIMARY KEY,
    house_id         INTEGER NOT NULL REFERENCES house(house_id),
    owner_player_id  UUID NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    is_locked        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE house_instance_guest (
    instance_id      BIGINT NOT NULL REFERENCES house_instance(instance_id) ON DELETE CASCADE,
    guest_player_id  UUID   NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    invited_by       UUID REFERENCES player(player_id) ON DELETE SET NULL,
    invited_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (instance_id, guest_player_id)
);

CREATE TABLE placed_object (
    placed_id    BIGSERIAL PRIMARY KEY,
    instance_id  BIGINT NOT NULL REFERENCES house_instance(instance_id) ON DELETE CASCADE,
    item_id      INTEGER NOT NULL REFERENCES item(item_id),
    pos_x        DOUBLE PRECISION,
    pos_y        DOUBLE PRECISION,
    pos_z        DOUBLE PRECISION,
    rot_yaw      DOUBLE PRECISION
);
