-------------------------------------------------------------------------------
-- Last update : Fri Jun 14 13:31:50 2019
-- Project     : VHDL Mode for Sublime Text
-------------------------------------------------------------------------------
-- Description: This VHDL file is intended as a test of scope and beautifier
-- functions for the VHDL Mode package.  It should never be actually compiled
-- as I do several strange things to make sure various aspects of beautification
-- and syntax scoping are checked.
-------------------------------------------------------------------------------
--------------------------------------------------------------------------------
-- VHDL-2008 package library use.
package master_bfm is new work.avalon_bfm_pkg
	generic map
	(
		G_DATA_WIDTH  => 32,
		G_ADDR_WIDTH  => 10,
		G_BURST_WIDTH => 4
	);
use work.master_bfm.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

/*
VHDL-2008 Block Comment
test zone.
*/

--/* Invalid layered
commenting */

--/* Valid layered
--   commenting */

-------------------------------------------------------------------------------
-- ENTITY STYLE TEST
-------------------------------------------------------------------------------
---------------------------------------
-- Sloppy Comment Test
-- Basically checking that comments are
-- preserved and do not affect
-- beautification or port copying.
---------------------------------------
-- Comment above
entity my_entity is                                                -- comments everywhere
	generic(                                                       -- I mean everywhere
		DATA_WIDTH          : integer                      := 8;   -- This value is 8
		REALLY_LONG_GENERIC : std_logic_vector(3 downto 0) := X"4" -- This comment should align with prior
	);                                                             -- Holy crap another comment -- with a comment inside the -- comment
	port (                                                         -- What about a comment here?
		                                                           -- Basic ports
		clk : in std_logic;
		-- Another comment on a line by itself!
		reset : in std_logic; -- And here's an inline comment.
		                      --d : in std_logic; -- Oh no! I commented out an actual line
		a, b, c : in  std_logic_vector(3 downto 0);
		q       : out std_logic); -- And finally
                                  -- A final
end entity my_entity;             -- Comment
                                  -- Comment below.

---------------------------------------
-- Blank Entity (and variations)
---------------------------------------
entity foobar is

end entity foobar;

entity entity_1 is

end entity_1;

entity entity_1 is

end entity;

package foo2 is

end package foo2;

package body foo2 is

end package body foo2;

architecture test of thing is

begin

end architecture test;

configuration MY_IDENT of thing is

end configuration MY_IDENT;

---------------------------------------
-- K&R Style Approximate.  entity/end
-- form the main block which shares the
-- same indent level, and inside opening
-- parens are on the same line as the
-- keyword, closing parens are at same
-- level as keyword.
---------------------------------------
entity kr_style_entity is
	generic (
		item_1   : type;
		item_12  : type        := default;
		item_123 : longer_type := other_default
	);
	port (
		item_1     : in    type;
		item_12    : out   type;
		item_123   : inout type             := default;
		item_1234  :       type(3 downto 0) := X"4";
		item_12345 : out   type
	);
end entity kr_style_entity;

---------------------------------------
-- Allman Style (C Style).  Parens share
-- same indent level as associated keyword
---------------------------------------
entity allman_style_entity is
	generic
	(
		item_1   : type;
		item_12  : type        := default;
		item_123 : longer_type := other_default
	);
	port
	(
		item_1     : in    type;
		item_12    : out   type;
		item_123   : inout type             := default;
		item_1234  : in    type(3 downto 0) := X"4";
		item_12345 : out   type
	);
end entity allman_style_entity;

---------------------------------------
-- Lisp Style: emacs vhdl-mode style
-- with the closing paren on the final
-- item line.
---------------------------------------
entity lisp_style_entity is
	generic (
		item_1   : type;
		item_12  : type        := default;
		item_123 : longer_type := other_default);
	port (
		item_1     : in    type;
		item_12    : out   type;
		item_123   : inout type             := default;
		item_1234  : in    type(3 downto 0) := X"4";
		item_12345 : out   type);
end entity lisp_style_entity;

--------------------------------------------------------------------------------
-- EXTENDED ENTITY TEST -- Uses the passive statements, assertion, a passive
-- procedure, a passive process.  VHDL-2008 inclusion of PSL Directives is
-- beyond the scope of this as I don't have a PSL syntax file.
--------------------------------------------------------------------------------
entity passive_test is
	generic (
		G_ADDR_WIDTH : integer := 10;
		G_DATA_WIDTH : integer := 8
	);
	port (
		clk      : in  std_logic;
		reset    : in  std_logic;
		addr     : in  std_logic_vector(G_ADDR_WIDTH-1 downto 0);
		data_in  : in  std_logic_vector(G_DATA_WIDTH-1 downto 0);
		we       : in  std_logic;
		data_out : out std_logic_vector(G_DATA_WIDTH-1 downto 0)
	);
begin
	CHECK : assert (G_DATA_WIDTH <= 32)
		report "ERROR : DATA WIDTH TOO LARGE (>32)"
		severity ERROR;
	TIME_CHECK : process (we) is
	begin
		if (we = '1') then
			report "MEMORY WRITTEN AT TIME" & to_string(now);
		end if;
	end process TIME_CHECK;
	my_passive_procedure(clk, addr, result);
end entity passive_test;

-------------------------------------------------------------------------------
-- END ENTITY TEST
-------------------------------------------------------------------------------
------------------------------------------------------------------------------
-- INDENT LEVEL SHOULD BE AT LEVEL 0 HERE IF ALL TESTS PASS
-------------------------------------------------------------------------------

configuration foobar of my_entity is
	use work.my_package.all;
	for rtl
		use lala.other_thing.all;
	end for;
end configuration foobar;

architecture rtl of my_entity is

	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------
	-------------------------------------------------------------------------------
	-- COMPONENT STYLE TEST.  Also checking lexing of variations in optional
	-- words for components.
	-------------------------------------------------------------------------------
	-- K&R Style
	component kr_style_component is
		generic (
			DATA_WIDTH          : integer                      := 8;
			REALLY_LONG_GENERIC : std_logic_vector(3 downto 0) := X"4"
		);
		port (
			clk     : in  std_logic;
			reset   : in  std_logic;
			a, b, c : in  std_logic_vector(3 downto 0);
			q       : out std_logic
		);
	end component kr_style_component;

	-- Allman Style
	component allman_style_component
		generic
		(
			DATA_WIDTH          : integer                      := 8;
			REALLY_LONG_GENERIC : std_logic_vector(3 downto 0) := X"4"
		);
		port
		(
			clk     : in  std_logic;
			reset   : in  std_logic;
			a, b, c : in  std_logic_vector(3 downto 0);
			q       : out std_logic
		);
	end component allman_style_component;

	-- Lisp Style
	component lisp_style_component is
		generic (
			DATA_WIDTH          : integer                      := 8;
			REALLY_LONG_GENERIC : std_logic_vector(3 downto 0) := X"4");
		port (
			clk     : in  std_logic;
			reset   : in  std_logic;
			a, b, c : in  std_logic_vector(3 downto 0);
			q       : out std_logic);
	end component;

	-------------------------------------------------------------------------------
	-- END COMPONENT STYLE
	-------------------------------------------------------------------------------
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------

	-------------------------------------------------------------------------------
	-- SIGNALS TEST
	-------------------------------------------------------------------------------
	signal my_signal_1 : std_logic;
	signal my_signal_2 : std_logic_vector(3 downto 0);
	signal a, b, c     : std_logic := '1';
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------

	constant C_CLOCK_PERIOD   : real                          := 1.23e-9;
	constant MY_PI            : real                          := 3.141592654;
	constant C_FOO, C_BAR     : integer                       := 999;
	constant C_OPERATOR_CHECK : std_logic_vector(31 downto 0) :=
		std_logic_vector(to_unsigned(1, 8)) &
		std_logic_vector(to_unsigned(2, 8)) &
		std_logic_vector(to_unsigned(3, 8)) &
		std_logic_vector(to_unsigned(4, 8));

	alias slv is std_logic_vector;
	alias 'c' is letter_c;
	alias + is plus;
	alias bus_rev : std_logic_vector is bus_thing;

begin
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------
	-------------------------------------------------------------------------------
	-- INSTANTIATION TESTS
	-------------------------------------------------------------------------------
	-- Direct entity instantiation tests.
	-- K&R Style
	my_entity_1 : entity work.my_entity
		generic map (
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC
		)
		port map (
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b,
			c     => c,
			q     => q
		);

	-- Allman Style
	my_entity_1 : entity work.my_entity
		generic map
		(
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC
		)
		port map
		(
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b,
			c     => c,
			q     => q
		);

	-- Lisp Style
	my_entity_1 : entity work.my_entity
		generic map (
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC)
		port map (
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b,
			c     => c,
			q     => q);

	-- Component instantiation tests
	-- K&R Style
	my_entity_1 : component my_entity
		generic map (
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC
		)
		port map (
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b,
			c     => c,
			q     => q
		);

	-- Allman Style
	my_entity_1 : my_entity
		generic map
		(
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC
		)
		port map
		(
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b,
			c     => c,
			q     => q
		);

	-- Lisp Style
	my_entity_1 : my_entity
		generic map (
			DATA_WIDTH          => DATA_WIDTH,
			REALLY_LONG_GENERIC => REALLY_LONG_GENERIC)
		port map (
			clk           => clk,
			reset         => reset,
			a             => a,
			b             => b,
			c             => c,
			q             => q,
			x(1)          => z,
			y(3 downto 0) => 9,
			z(x'range)    => zz);

	i_if_cpu : if_cpu
		port map (
			clk   => clk,
			reset => reset,
			a     => a,
			b     => b
		);

	-------------------------------------------------------------------------------
	-- END OF INSTANTIATION TESTS
	-------------------------------------------------------------------------------
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------

	-------------------------------------------------------------------------------
	-- MIXED CODE TESTS
	-------------------------------------------------------------------------------
	SEQUENTIAL_PROCESS : process (clk, reset)
		variable my_variable  : integer;
		shared variable alpha : std_logic_vector(31 downto 0);
	begin
		-- If/then normal style
		IF_LABEL : if (reset = '1') then
			q1         <= '0';
			q2_long    <= '1';
			q3         <= b"1010Y";
			octal_test <= 12o"01234567_XY";
			hex_test   := 7X"0123456789--aAbBcCdDeEfF_XY"; -- Comment
			bool_test  := true;
		elsif rising_edge(clk) then
			if (ce = '1') then
				q1      <= d1;
				q2_long <= d2_long;
				-- Some syntax number matching.
				x0 <= 25_6;
				x1 <= 16#1234_ABCD_EF#;
				x2 <= 10#1024#E+00;
				x3 <= 1_024e-9;
				y0 <= 3.141_592_654;
				y1 <= 1_2.5e-9;
				y2 <= 2#0.1_0#;
				y3 <= 10#10_24.0#E+00;

				z0 <= math_pi;
				a  <= 3 + 4;

				pt1 <= 0;
				pt2 <= (0);
			end if;
		end if;

		-- If/then Leo style (heaven help us)
		if (my_condition_a = 1)
		then a <= b;
		elsif (my_condition_b = 2)
		then c <= d;
		else e <= f;
		end if;

		-- Extremely long conditional test
		if (((a and b) and (x or y) or
				((m or n) and c
				or d) and
				boolean)) then
			g <= h;
		end if;

		-- Case test long form
		CASE_LABEL : case my_tester is
			when 1 =>
				a <= b;
				c <= d;
			when 2 =>
				e <= f;
				g <= h;
			when 3 =>
				i <= j;
				k <= l;
			when 4 =>
				foo <= (others => '0');
			when others =>
				null;
		end case CASE_LABEL;

		-- Case test compact form
		-- The fix for the alignment of => breaks alignment here, but it's
		-- probably okay.  Compact is already readable.
		case my_test is
			 when a      => a      <= b;
			 when c      => c      <= d;
			 when others => e <= f;
		end case;

		-- Case test for alignment of => in a case statement.
		case my_alignment_test is
			when a                      =>
				long_signal_name <= (others => '0');
			when b =>
				another_long_name <= (others => '0');
			when others =>
				a_third_long_name <= (others => '0');
		end case;
	end process SEQUENTIAL_PROCESS;
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------

	COMBINATORIAL_PROCESS : process (all)
	begin
		wait;
		wait until (a > b);
		wait for 10 ns;

		-- Procedure calls
		SUBPROGRAM_CALL_LABEL : my_subprogram_call(values);

		ANOTHER_CALL : some_write(L, string'("Text"));

		write(L, string'("foobar"));

		std.env.stop(0);

		stop(0);

		-- Loop tests
		MY_BASIC_LOOP : loop

		end loop MY_BASIC_LOOP;

		MY_LOOP : loop

			MY_INNER_LOOP : loop
				next;
			end loop MY_INNER_LOOP;

			MY_WHILE_LOOP : while (a > b) loop
				a <= b;
			end loop;

			exit;
		end loop MY_LOOP;

		MY_FOR_LOOP : for index in 0 to 9 loop
			if (condition) then
				a       := b;
				counter := counter + 1;
			else
				next;
			end if;
		end loop MY_FOR_LOOP;

	end process COMBINATORIAL_PROCESS;

	-------------------------------------------------------------------------------
	-- Process name variations
	-------------------------------------------------------------------------------
	process (clk, reset)
	begin
		if (reset = '1') then

		elsif rising_edge(clk) then

		end if;
	end process;

	LABEL : process (clk, reset)
	begin
		if (reset = '1') then

		elsif rising_edge(clk) then

		end if;
	end process;

	LABEL : postponed process (clk, reset)
	begin
		if (reset = '1') then

		elsif rising_edge(clk) then

		end if;
	end postponed process LABEL;
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------
	-- Assignment statements
	foo                             <= bar;
	foo(99)                         <= signal_name;
	foo(15 downto 0)                <= other_signal_name(15 downto 0);
	foo(some_signal'range)          <= yet_another_name'range;
	foo(other_signal'reverse_range) <= foo(15 downto 0);
	foo(to_integer(my_unsigned))    <= 97;

	foo(some_signal'range)          <= yet_another_name'range;
	foo(other_signal'reverse_range) <= foo(15 downto 0);
	adder1                          <= ( '0' & add_l) + ( '0' & add_m);
	adder2                          <= ("0" & add_r) + ('0' & add_b);
	adder                           <= ('0' & adder1) + ('0' & adder2);

	bus_rw <= '1' when (condition) else '0';

	mux_output <= selection_1 when condition else
		selection_2 when condition else
		selection_3 when condition else
		selection_4 when others;

	mux_output <=
		selection_1 when condition else
		selection_2 when condition else
		selection_3 when condition else
		selection_4 when others;

	with my_signal select
	address <=
		adc_addr         when choice1,
		temp_sensor_addr when choice2,
		light_sense_addr when choice3,
		X"0000"          when others;

	with my_signal select
	a <= adc_addr when choice1,
		temp_sensor_addr when choice2,
		light_sense_addr when choice3,
		X"0000"          when others;

	with my_signal select a <=
		tiny        when choice1,
		bigger      when choice2,
		really_long when choice3,
		X"0000"     when others;

	data_bus_miso <=
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"00000001" when (std_match(addr_bus, C_MY_ADDRESS_1)),
		X"FFFFFFFF" when others;

	assert (condition)
		report "This string would \nget printed in a simulator. -- Comment Test /* Other comment test */"
		severity WARNING;
	-------------------------------------------------------------------------------
	-- INDENT LEVEL SHOULD BE AT LEVEL 1 HERE
	-------------------------------------------------------------------------------

	MY_GENERATOR : for x in 0 to 7 generate
		signal a : std_logic;
	begin
		x <= a;
	end generate MY_GENERATOR;

	for i in foobar'range generate

	end generate;

	for x in std_logic_vector generate

	end generate;

	for index in 0 to 9 generate

	end generate;

	MY_THING : if (x>1) generate

	else

	elsif (y<0) generate

	end generate;

	MY_CASE_GEN : case thing generate
	when choice =>

	when choice =>

	end generate MY_CASE_GEN;


end architecture rtl;

-------------------------------------------------------------------------------
-- Syntax testing some architecture end clause variations.
-------------------------------------------------------------------------------
architecture testing of my_entity is

begin

end architecture testing;

architecture testing of my_entity is

begin

end testing;

architecture testing of my_entity is

begin

end architecture;

architecture testing of my_entity is

begin

end;
-------------------------------------------------------------------------------
-- PACKAGE, PROCEDURE, AND FUNCTION TESTS
-------------------------------------------------------------------------------
package my_package is

	-------------------------------------------------------------------------------
	-- Type and constant declarations
	-------------------------------------------------------------------------------
	-- Fairly simple enumerated type.
	type MY_STATES is (IDLE, STATE1, STATE2, STATE3);

	-- Enumerated type with entries on different lines
	type MY_STATES is
		(
			IDLE,
			S1,
			S2,
			S3
		);

	-- Complex type with record
	type T_MY_TYPE is record
		name             : type;
		name             : type;
		name             : type(3 downto 0);
		name             : other_type;
		really_long_name : yat;
		a, b, c          : std_logic;
	end record;

	type T_MY_ARRAY_TYPE is array (3 downto 0) of integer;
	type word is array (0 to 31) of bit;
	type state_counts is array (idle to error) of natural;
	type state_counts is array (controller_state range idle to error) of natural;
	type coeff_array is array (coeff_ram_address'reverse_range) of real;
	type my_range is range 0 to 31;
	type bit_index is range 0 to number_of_bits-1;
	type resistance is range 0 to 1e9 units
		ohm;
		kohm = 1000 ohm;
		Mohm = 1000 kohm;
	end units resistance;

	-- Simple constant
	constant C_CLOCK_SPEED : real := 3.75e-9; -- seconds

	-- Complex constant
	constant C_MY_BFM_INIT : T_MY_TYPE :=
		(
			clk       => 'z',
			addr      => (others => '0'),
			addr_data => (others => '0'),
			oe_n      => 'z',
			gta_n     => 'z'
		);

	-------------------------------------------------------------------------------
	-- Procedure Declarations
	-------------------------------------------------------------------------------
	-- K&R Style
	procedure another_procedure (
			signal name       : inout type;
			name              : in    type2;
			variable data_out : out   std_logic_vector(3 downto 0);
			debug             : in    boolean := FALSE
		);

	-- Allman Style.  It looks a little like the GNU style because parens are
	-- indented, however it's only because these are being treated as the code
	-- block.  Might be able to mix it up a little with the continuation
	-- clauses.
	procedure my_init_procedure
		(
			signal name : inout type
		);

	-- Lisp Style
	procedure another_procedure (
			signal name       : inout type;
			name              : in    type2;
			variable data_out : out   std_logic_vector(3 downto 0);
			debug             : in    boolean := FALSE);

	-------------------------------------------------------------------------------
	-- Function Declarations
	-------------------------------------------------------------------------------
	-- One line style
	function reverse_bus (bus_in : in std_logic_vector) return std_logic_vector;

	-- K&R Style
	function equal_with_tol (
			a   : in unsigned;
			b   : in unsigned;
			tol : in integer
		) return boolean;

	-- Allman Style
	function equal_with_tol
		(
			a   : in unsigned;
			b   : in unsigned;
			tol : in integer
		) return boolean;

	-- Lisp Style
	function equal_with_tol (
			a   : in unsigned;
			b   : in unsigned;
			tol : in integer) return boolean;

end package my_package;

package body my_package is

	-------------------------------------------------------------------------------
	-- Procedure Body Tests
	-------------------------------------------------------------------------------
	-- K&R Style
	procedure elbc_gpcm_init (
			signal elbc_if_rec : inout T_ELBC_GPCM_IF
		) is
	begin
		elbc_if_rec.addr      <= (others => 'Z');
		elbc_if_rec.addr_data <= (others => 'Z');
		elbc_if_rec.cs_n      <= (others => '1');
		elbc_if_rec.oe_n      <= '1';
		elbc_if_rec.we_n      <= (others => '1');
		elbc_if_rec.ale       <= '0';
		elbc_if_rec.ctrl      <= '1';
		elbc_if_rec.gta_n     <= 'Z';
	end procedure elbc_gpcm_init;

	-- Allman Style
	procedure elbc_gpcm_init
		(
			signal elbc_if_rec : inout T_ELBC_GPCM_IF
		) is
	begin
		elbc_if_rec.addr      <= (others => 'Z');
		elbc_if_rec.addr_data <= (others => 'Z');
		elbc_if_rec.cs_n      <= (others => '1');
		elbc_if_rec.oe_n      <= '1';
		elbc_if_rec.we_n      <= (others => '1');
		elbc_if_rec.ale       <= '0';
		elbc_if_rec.ctrl      <= '1';
		elbc_if_rec.gta_n     <= 'Z';
	end procedure elbc_gpcm_init;

	-- Lisp Style
	procedure elbc_gpcm_init (
			signal elbc_if_rec : inout T_ELBC_GPCM_IF) is
	begin
		elbc_if_rec.addr      <= (others => 'Z');
		elbc_if_rec.addr_data <= (others => 'Z');
		elbc_if_rec.cs_n      <= (others => '1');
		elbc_if_rec.oe_n      <= '1';
		elbc_if_rec.we_n      <= (others => '1');
		elbc_if_rec.ale       <= '0';
		elbc_if_rec.ctrl      <= '1';
		elbc_if_rec.gta_n     <= 'Z';
	end procedure elbc_gpcm_init;

	-------------------------------------------------------------------------------
	-- Function Body Tests
	-------------------------------------------------------------------------------
	-- Single line style.
	function reverse_bus (bus_in : in slv) return slv is

		variable bus_out : std_logic_vector(bus_in'range);
		alias bus_in_rev : std_logic_vector(bus_in'reverse_range) is bus_in;

	begin
		for i in bus_in_rev'range loop
			bus_out(i) := bus_in_rev(i);
		end loop;

		return bus_out;
	end; -- function reverse_bus

	-- K&$ Style
	function equal_with_tol (
			a   : in unsigned;
			b   : in unsigned;
			tol :    integer
		) return boolean is
		variable low_limit  : unsigned(b'range);
		variable high_limit : unsigned(b'range);
		variable foo, bar   : std_logic;
	begin
		low_limit  := b - tol;
		high_limit := b + tol;
		if (a >= low_limit and a <= high_limit) then
			return TRUE;
		else
			return FALSE;
		end if;

	end function equal_with_tol;

	-- Allman Style
	function equal_with_tol
		(
			a   : in unsigned;
			b   : in unsigned;
			tol :    integer
		) return boolean is
		variable low_limit  : unsigned(b'range);
		variable high_limit : unsigned(b'range);
	begin
		low_limit  := b - tol;
		high_limit := b + tol;
		if (a >= low_limit and a <= high_limit) then
			return TRUE;
		else
			return FALSE;
		end if;

	end function equal_with_tol;

	-- Lisp Style
	function onehot_vector (
			size  : in integer;
			index : in integer) return slv is
		variable vector_out : std_logic_vector(size-1 downto 0);
	begin
		for i in vector_out'range loop
			if (i = index) then
				vector_out(i) := '1';
			else
				vector_out(i) := '0';
			end if;
		end loop;
		return vector_out;
	end function onehot_vector;

	-- Padding function
	function make_miso_word (d_in : std_logic_vector)
		return std_logic_vector is
		variable d_out : std_logic_vector(C_SPI_DATA_LEN-1 downto 0);
	begin
	end function make_miso_word;


end package body my_package;
