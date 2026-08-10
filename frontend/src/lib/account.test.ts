import { describe, expect, it } from "vitest";

import { initials } from "./account";

describe("initials", () => {
  it("takes one letter from each name", () => {
    expect(initials({ first_name: "Priya", last_name: "Nair" })).toBe("PN");
  });

  it("uppercases whatever it is given", () => {
    expect(initials({ first_name: "priya", last_name: "nair" })).toBe("PN");
  });

  it("falls back rather than rendering nothing", () => {
    // An empty circle in the header reads as a broken image. A "?" reads as
    // an account with no name, which is what it is.
    expect(initials(null)).toBe("?");
    expect(initials({ first_name: "", last_name: "" })).toBe("?");
  });

  it("copes with a single name", () => {
    expect(initials({ first_name: "Prince", last_name: "" })).toBe("P");
  });

  it("takes the first character of a name that starts with an accent", () => {
    expect(initials({ first_name: "Émile", last_name: "Zola" })).toBe("ÉZ");
  });
});
