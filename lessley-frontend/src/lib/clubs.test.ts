import { describe, expect, it } from "vitest"

import { normalizeClubId, resolveClubName } from "./clubs"
import type { ClubDto } from "./types"

// The live clubs collection: un-suffixed parents only. Deals carry tier variants of
// the two PaisPlus cards that have no record of their own here.
const CLUBS: ClubDto[] = [
  { id: "club_hot", name: "HOT Israel" },
  { id: "club_paisplus", name: "PaisPlus" },
  { id: "club_paisplus_networks", name: "PaisPlus — Networks Cash Card" },
  { id: "club_paisplus_food_chains", name: "PaisPlus — Food Chains Cash Card" },
  { id: "club_mastercard", name: "Mastercard Israel" },
]

describe("normalizeClubId", () => {
  it("strips the club_ prefix, the llm: scheme and hyphenation", () => {
    expect(normalizeClubId("club_hot")).toBe("hot")
    expect(normalizeClubId("llm:hever-gift-card-company")).toBe("hever_gift_card_company")
    expect(normalizeClubId("  HOT  ")).toBe("hot")
  })
})

describe("resolveClubName", () => {
  it("resolves the club_id a deal card carries", () => {
    expect(resolveClubName(CLUBS, "club_mastercard")).toBe("Mastercard Israel")
  })

  it("resolves a bare source_id, which is all a stack step has", () => {
    expect(resolveClubName(CLUBS, undefined, "hot")).toBe("HOT Israel")
  })

  it("resolves a tier variant back to its parent club", () => {
    expect(resolveClubName(CLUBS, "club_paisplus_networks_regular")).toBe(
      "PaisPlus — Networks Cash Card",
    )
    expect(resolveClubName(CLUBS, undefined, "paisplus_food_chains_vip")).toBe(
      "PaisPlus — Food Chains Cash Card",
    )
  })

  it("does not let a tier variant match a different club that shares its stem", () => {
    // `paisplus_networks_regular` must not fall through to plain `PaisPlus`.
    expect(resolveClubName(CLUBS, "club_paisplus_networks_vip")).toBe(
      "PaisPlus — Networks Cash Card",
    )
    expect(resolveClubName(CLUBS, "club_paisplus")).toBe("PaisPlus")
  })

  it("prefers club_id over source_id when both are present", () => {
    expect(resolveClubName(CLUBS, "club_mastercard", "hot")).toBe("Mastercard Israel")
  })

  it("falls back to the raw id rather than rendering nothing", () => {
    expect(resolveClubName(CLUBS, "club_behatsdaa")).toBe("club_behatsdaa")
  })

  it("returns null when the deal carries no club at all", () => {
    expect(resolveClubName(CLUBS, null, undefined)).toBeNull()
    expect(resolveClubName(CLUBS, "   ")).toBeNull()
  })
})
