#include <stdint.h>
/*
 * main.c
 *
 *  Created on: 17 dic. 2017
 *      Author: sapista
 *      comm..
 */


#define F_CPU 16000000UL // 16 MHz

#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <util/delay.h>
#include <util/atomic.h>
#include <stdio.h>
#include "uart.h"
#include "fader.h"
#include "raspSerial.h"

//#define ENCODER_THRESHOLD 8 //Minimum encoder increment to filter out bouncing artefacts //TODO remove this

#define TX_TICK_MAX 150 //Ticks max in ms for the throttling of serial TX 

volatile int8_t encoder_detent_events = 0; // Increments of +1 or -1 sent to UART

static inline void handle_encoder_change(void) {
    static int8_t store = 0;
    static uint8_t prev_state = 0;

    // 1. Read pins
    uint8_t curr_state = (PIND & ((1 << PD0) | (1 << PD1))) >> PD0;
    
    // 2. State lookup table (-1, 0, +1)
    static const int8_t valid_states[] = {
         0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0
    };

    uint8_t index = (prev_state << 2) | curr_state;
    int8_t step = valid_states[index];

    if (step != 0) {
        store += step;
        prev_state = curr_state;

        // 3. ONLY commit when we land back on the resting detent state (00)
        if (curr_state == 0b00) {
            if (store >= 4) {
                encoder_detent_events++; // Full CW click completed
            } else if (store <= -4) {
                encoder_detent_events--; // Full CCW click completed
            }
            store = 0; // Reset accumulator for the next detent
        }
    }
}

ISR(INT0_vect) { handle_encoder_change(); }
ISR(INT1_vect) { handle_encoder_change(); }


int main()
{
	DDRC |= (1<<PF0); //Testing LED pin as output;


	// Config and init UART
  uart_init();
  stdout = &uart_output;
  stdin = &uart_input;

    //Fader Vars
	uint16_t _targets[NUM_OF_FADERS];
	uint16_t _position[NUM_OF_FADERS];
	uint16_t _touchValues[NUM_OF_FADERS];
	uint8_t faderTouched_ant = 0x00; //Store the previous touch state

	//Initialize all data fields requested by faders
	set_fposition_ptr(_position);
	set_ftarget_ptr(_targets);
	set_touchValues_ptr(_touchValues);

	//Init Faders
	initFaders();
	startMotorController();

	//Init raspberry pi serial communications
	picom_handler_t picom = picom_init();
	picom_add_setFaderValueCallback(picom, setFaderTarget);

	//Encoder initialization
	DDRD &=~ (1 << PD0);				// PD0 and PD1 as input
	DDRD &=~ (1 << PD1);
	//PORTD |= (1 << PD0)|(1 << PD1);   // PD0 and PD1 pull-up enabled #TODO remove

	EIMSK |= (1<<INT0)|(1<<INT1);		// enable INT0 and INT1
	EICRA |= (1<<ISC00)|(1<<ISC10); // Falling and reising edges

	calibrateTouchSensors(); //always calibrate touch sensors at the start

	//Global Interrupts enable
	sei();

  while(1)
	{
/*DEBUG prints
		PORTF |= (1<<PF0); //LED on
		_delay_ms(500);
		if( getTouchedFader() )
		{
			_delay_ms(500);
		}
		PORTF &= ~(1<<PF0); //LED off
		if( !getTouchedFader() )
		{
			_delay_ms(500);
		}


		uint8_t icounttest = 0;
		printf("Int Number test: %d\n", icounttest);
		icounttest++;

		for( uint8_t i = 0; i < NUM_OF_FADERS; i++)
		{
			printf("Fader%u: Pos:%u\tTocuh(%u):%u\n", i+1, _position[i], 0x01&(getTouchedFader()>>i), _touchValues[i]);
		}

*/

		//Process incoming queue
		picom_process_RX_queue(picom);

		//Delay to throttle down the serial com
		//_delay_ms(5);

		//Check for encoder changes to send
		uint8_t encoder_send_val;
		ATOMIC_BLOCK(ATOMIC_FORCEON)
		{
			encoder_send_val = encoder_detent_events;
			encoder_detent_events = 0;
		}

		if(encoder_send_val != 0)
		{
			picom_TXqueue_append_EncoderValue(picom, encoder_send_val);
			picom_process_TX_queue(picom); //Try to send at least the first byte
		}

		//Check for fader changes to send
		uint8_t fader_changed = getFaderChanged();
		uint8_t faderTouched = getTouchedFader();
		uint8_t fader_UnTouchFlags = 0;
		for( uint8_t i = 0; i < NUM_OF_FADERS; i++)
		{
			//Check if current fader has data to send
			if(fader_changed & (1<<i))
			{
				picom_TXqueue_append_faderValue(picom, i, getFaderPosition(i));
				acknowledgeFaderChanged(i); //Avoid re-sending the same data by clearing the change state
				picom_process_TX_queue(picom); //Try to send at least the first byte
			}

			//Check if current fader has been untouched
			if( (faderTouched_ant & (1<<i)) && !(faderTouched & (1<<i)) )
			{
				//Fader untouched event
				fader_UnTouchFlags |= (1<<i);
			}
		}

		if(fader_UnTouchFlags)
		{
			picom_TXqueue_append_faderUntouched(picom, fader_UnTouchFlags);
			picom_process_TX_queue(picom);
		}

		picom_process_TX_queue(picom); //Ensure second byte is sent
		faderTouched_ant = faderTouched; //Update fader touch ant
	}

	return 0;
}
